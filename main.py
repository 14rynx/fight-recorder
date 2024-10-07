import contextlib
import json
import logging
import os
import sys
import threading
import urllib.request
import zipfile
from enum import Enum

import customtkinter as ctk
import pystray
import win32com.client
from PIL import Image

from listener_thread import run, RecordingStatusCallback
from video_processing import ProcessingStatusCallback, VideoProcessingPipeline

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s', filename="main.log")
logger = logging.getLogger("main")


class RecordingStatus(Enum):
    INIT = 1
    READY = 2
    RECORDING = 3
    ERROR = 4


class ProcessingStatus(Enum):
    INIT = 1
    READY = 2
    PROCESSING = 3
    ERROR = 4


class FightRecorderApp:
    default_settings = {
        "OBS_HOST": "localhost",
        "OBS_PORT": "",
        "OBS_PASSWORD": "",
        "OBS_DIRECTORY": "",
        "TIMEOUT": "60",
        "CONCATENATE_OUTPUTS": True,
        "DELETE_ORIGINALS": True,
        "LOG_DIR": "",
        "OUTPUT_DIR": ""
    }

    def __init__(self, root):
        self.root = root

        # Figure out if packaged exe or not
        self.packaged = getattr(sys, 'frozen', False)
        logger.info(f"App is packaged {self.packaged}")

        # Setup required paths
        self.settings_path = 'settings.json'

        # Figure out path for persistency script
        link_dir = f"{os.environ['APPDATA']}\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        self.link_path = os.path.join(link_dir, "Fight_Recorder.lnk")
        self.bat_path = os.path.join(link_dir, "Fight_Recorder.bat")

        # Figure out base path for resources
        if self.packaged:
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.abspath(".")

        # Load Settings
        try:
            with open(self.settings_path, 'r') as f:
                self.settings = json.load(f)
            logger.info("Loaded settings.")
        except FileNotFoundError:
            self.settings = {}
            logger.warning("Loading settings failed, running defaults.")

        # Write default settings for all keys that do not exist
        has_changed = False
        for key, value in self.default_settings.items():
            if key not in self.settings:
                self.settings[key] = value
                has_changed = True

        # Download Ffmpeg if required
        self.check_ffmpeg()

        if has_changed:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)

        # Draw Main Window
        self.root.title("Fight Recorder")
        self.root.iconbitmap(os.path.join(self.base_path, "data", "orange.ico"))

        # Status of Programm
        self.recording_status = RecordingStatus.INIT
        self.processing_status = ProcessingStatus.INIT
        self.error_message = ""
        self.is_minimized = False

        # Make Thread Relevant Setup
        self.stop_event = threading.Event()
        self.listener_thread = None

        # Setup event callback
        self.root.protocol('WM_DELETE_WINDOW', self.exit)
        self.root.bind("<Unmap>", self.minimize_to_tray)
        self.root.bind('<Control-s>', self.save_and_run)

        # Draw main ui
        self.draw_ui()

        # Build tray icon
        menu = (pystray.MenuItem('Show', self.show_from_tray, default=True),
                pystray.MenuItem('Quit', self.exit))
        image = Image.open(os.path.join(self.base_path, "data", "orange.ico"))
        self.icon = pystray.Icon("flightrecorder", image, "Fight Recorder", menu)
        self.tray_thread = threading.Thread(target=lambda: self.icon.run(), daemon=True)
        self.tray_thread.start()

        # Start working
        self.get_autostart()
        self.start_listener()
        self.auto_minimize()

    def auto_minimize(self):
        """check status and automatically minimize as soon as everything is ok"""
        if len(sys.argv) > 1 and sys.argv[1] in ["-m", "--minimize"]:
            if self.recording_status is RecordingStatus.READY and self.processing_status is ProcessingStatus.READY:
                self.minimize_to_tray()

            # Try again later if we did not run into any errors yet
            elif self.recording_status is RecordingStatus.INIT or self.processing_status is ProcessingStatus.INIT:
                self.root.after(1000, self.auto_minimize)

    def draw_ui(self):
        """draw the user interface"""
        # OBS Frame
        self.obs_frame = ctk.CTkFrame(master=self.root)
        self.obs_frame.grid(row=0, column=0, padx=10, pady=5, sticky='wnes')

        self.obs_frame_title = ctk.CTkLabel(self.obs_frame, text="OBS Settings")
        self.obs_frame_title.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        # OBS Host
        self.obs_host_label = ctk.CTkLabel(self.obs_frame, text="Host:")
        self.obs_host_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.obs_host_entry = ctk.CTkEntry(self.obs_frame, border_width=0)
        self.obs_host_entry.insert(0, self.settings.get('OBS_HOST', ''))
        self.obs_host_entry.bind('<FocusOut>', self.save_and_run)
        self.obs_host_entry.grid(row=1, column=1, sticky="e", padx=10, pady=5)

        # OBS Port
        self.obs_port_label = ctk.CTkLabel(self.obs_frame, text="Port:")
        self.obs_port_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)

        self.obs_port_entry = ctk.CTkEntry(self.obs_frame, border_width=0)
        self.obs_port_entry.insert(0, self.settings.get('OBS_PORT', ''))
        self.obs_port_entry.bind('<FocusOut>', self.save_and_run)
        self.obs_port_entry.grid(row=2, column=1, sticky="e", padx=10, pady=5)

        # OBS Password
        self.obs_password_label = ctk.CTkLabel(self.obs_frame, text="Password:")
        self.obs_password_label.grid(row=3, column=0, sticky="w", padx=10, pady=5)

        self.obs_password_entry = ctk.CTkEntry(self.obs_frame, show='*', border_width=0)
        self.obs_password_entry.insert(0, self.settings.get('OBS_PASSWORD', ''))
        self.obs_password_entry.bind('<FocusOut>', self.save_and_run)
        self.obs_password_entry.grid(row=3, column=1, sticky="e", padx=10, pady=5)

        # ---------------------------------------------------------------------
        # Behaviour Frame
        self.behaviour_frame = ctk.CTkFrame(master=self.root)
        self.behaviour_frame.grid(row=0, column=1, padx=10, pady=5, sticky='wne')

        self.behaviour_frame_title = ctk.CTkLabel(self.behaviour_frame, text="Behaviour Settings")
        self.behaviour_frame_title.grid(row=0, column=0, sticky='w', padx=10, pady=10)

        # Timeout
        self.timeout_label = ctk.CTkLabel(self.behaviour_frame, text="Timeout (seconds):")
        self.timeout_label.grid(row=1, column=0, sticky='we', padx=10, pady=5)

        self.timeout_entry = ctk.CTkEntry(self.behaviour_frame, border_width=0)
        self.timeout_entry.insert(0, self.settings.get('TIMEOUT', ''))
        self.timeout_entry.bind('<FocusOut>', self.save_and_run)
        self.timeout_entry.grid(row=1, column=1, sticky='we', padx=10, pady=5)

        # Concatenate Outputs
        self.concatenate_outputs_var = ctk.BooleanVar()
        self.concatenate_outputs_var.set(self.settings.get('CONCATENATE_OUTPUTS', False))
        self.concatenate_outputs_checkbox = ctk.CTkCheckBox(
            self.behaviour_frame,
            text="Concatenate output Videos",
            variable=self.concatenate_outputs_var,
            command=self.save_and_run
        )
        self.concatenate_outputs_checkbox.grid(row=2, column=0, columnspan=3, sticky='w', padx=10, pady=5)

        self.manual_concatenate = ctk.CTkButton(
            self.behaviour_frame,
            text='Manually Concatenate',
            command=self.run_concatenate
        )
        self.manual_concatenate.grid(row=2, column=3, columnspan=2, sticky='e', padx=10, pady=5)

        # Delete Originals
        self.delete_originals_var = ctk.BooleanVar()
        self.delete_originals_var.set(self.settings.get('DELETE_ORIGINALS', False))
        self.delete_originals_checkbox = ctk.CTkCheckBox(
            self.behaviour_frame,
            text="Delete original Videos after Concatenation",
            variable=self.delete_originals_var,
            command=self.save_and_run
        )
        self.delete_originals_checkbox.grid(row=3, column=0, columnspan=3, sticky='w', padx=10, pady=5)

        # Run on Startup
        self.run_on_startup_var = ctk.BooleanVar()
        self.run_on_startup_var.set(self.settings.get('DELETE_ORIGINALS', False))
        self.run_on_startup_checkbox = ctk.CTkCheckBox(
            self.behaviour_frame,
            text="Run On Startup",
            variable=self.run_on_startup_var,
            command=self.set_autostart
        )
        self.run_on_startup_checkbox.grid(row=4, column=0, columnspan=3, sticky='w', padx=10, pady=5)

        # ---------------------------------------------------------------------
        # Directories Frame
        self.directory_frame = ctk.CTkFrame(master=self.root)
        self.directory_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='wne')

        self.directory_frame_title = ctk.CTkLabel(self.directory_frame, text="Directory Settings")
        self.directory_frame_title.grid(row=0, column=0, sticky='w', padx=10, pady=10)

        # Log Directory
        self.log_directory_label = ctk.CTkLabel(self.directory_frame, text="Log Directory:")
        self.log_directory_label.grid(row=1, column=0, sticky='w', padx=10, pady=5)

        self.log_directory = ctk.StringVar()
        self.log_directory.set(self.settings.get('LOG_DIR', ''))
        self.log_directory_entry = ctk.CTkEntry(self.directory_frame, textvariable=self.log_directory, width=350,
                                                border_width=0)
        self.log_directory_entry.bind('<FocusOut>', self.save_and_run)
        self.log_directory_entry.grid(row=1, column=1, sticky='we', padx=10, pady=5)

        self.log_directory_dialog = ctk.CTkButton(
            self.directory_frame,
            text='Open',
            command=self.select_log_directory
        )
        self.log_directory_dialog.grid(row=1, column=2, sticky='e', padx=10, pady=5)

        # Output Directory
        self.output_directory_label = ctk.CTkLabel(self.directory_frame, text="Output Directory:")
        self.output_directory_label.grid(row=2, column=0, sticky='w', padx=10, pady=5)

        self.output_directory = ctk.StringVar()
        self.output_directory.set(self.settings.get('OUTPUT_DIR', ''))
        self.output_directory_entry = ctk.CTkEntry(self.directory_frame, textvariable=self.output_directory, width=350,
                                                   border_width=0)
        self.output_directory_entry.bind('<FocusOut>', self.save_and_run)
        self.output_directory_entry.grid(row=2, column=1, sticky='we', padx=10, pady=5)

        self.output_directory_dialog = ctk.CTkButton(
            self.directory_frame,
            text='Open',
            command=self.select_output_directory
        )
        self.output_directory_dialog.grid(row=2, column=2, sticky='e', padx=10, pady=5)

        # ---------------------------------------------------------------------
        # Status Frame
        self.status_frame = ctk.CTkFrame(master=self.root)
        self.status_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='wne')

        self.status_frame_title = ctk.CTkLabel(self.status_frame, text="Status")
        self.status_frame_title.pack(side="left", padx=10, pady=10)

        self.status_subframe = ctk.CTkFrame(master=self.status_frame, fg_color="orange")
        self.status_subframe.pack(side="right", padx=5, pady=5)

        self.status_label = ctk.CTkLabel(self.status_subframe, text="Initializing")
        self.status_label.grid(row=1, column=0, sticky='e', padx=5, pady=5)

    def select_log_directory(self):
        """open a file dialog for log directory"""
        directory = ctk.filedialog.askdirectory()
        self.log_directory.set(directory)
        self.save_and_run()

    def select_output_directory(self):
        """open a file dialog for output directory"""
        directory = ctk.filedialog.askdirectory()
        self.output_directory.set(directory)
        self.save_and_run()

    def get_autostart(self):
        """check if there is a script / symlink so that the program will automatically start on user login"""
        if self.packaged:
            # It is ran as an executable -> Check for a shortcut
            self.run_on_startup_var.set(os.path.exists(self.link_path))
        else:
            # It is ran as a script -> Check for a bat file
            self.run_on_startup_var.set(os.path.exists(self.bat_path))

    def set_autostart(self):
        """setup a script / symlink so that the program will automatically start on user login"""
        if self.run_on_startup_var.get():
            if self.packaged:
                # It is ran as an executable -> Make a shortcut
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(self.link_path)
                shortcut.Targetpath = sys.executable
                shortcut.Arguments = "--minimize"
                shortcut.WorkingDirectory = os.path.dirname(sys.executable)
                shortcut.WindowStyle = 1  # 7 - Minimized, 3 - Maximized, 1 - Normal
                shortcut.save()

            else:
                # It is ran as a script -> Make a bat file to activate venv and start it
                main_file = os.path.realpath(__file__)
                directory = os.path.dirname(main_file)
                command = f"{directory}\\venv\\Scripts\\activate.bat && cd {directory} && start python {main_file} --minimize"
                with open(self.bat_path, "w+") as bat_file:
                    bat_file.write(command)

        else:
            # Try removing both kind of link files
            with contextlib.suppress(FileNotFoundError):
                os.remove(self.link_path)
            with contextlib.suppress(FileNotFoundError):
                os.remove(self.bat_path)

    def check_ffmpeg(self):
        """Check if ffmpeg.exe exists and download it if not"""

        ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2024-10-06-19-32/ffmpeg-n7.1-7-g63f5c007a7-win64-gpl-7.1.zip"

        if not os.path.exists("ffmpeg.exe"):
            logger.info(f"ffmpeg.exe not found. Downloading and extracting...")

            urllib.request.urlretrieve(ffmpeg_url, "ffmpeg.zip")

            with zipfile.ZipFile("ffmpeg.zip", 'r') as zip_ref:
                for file in zip_ref.infolist():
                    if file.filename.endswith('/bin/ffmpeg.exe'):
                        file.filename = "ffmpeg.exe"
                        zip_ref.extract(file, os.getcwd())

            os.remove("ffmpeg.zip")

            logger.info(f"Downloaded ffmpeg successfully.")
        else:
            logger.info(f"Ffmpeg already exists.")

    def save_and_run(self, event=None):
        """save settings and start / restart listener if needed"""
        changed = self.save_settings()
        if changed:
            self.start_listener()

    def start_listener(self, event=None):
        """start the thread listening to logfiles and starting recordings"""
        logger.info("(Re)started listener.")
        # Make sure to not kill running recording
        if self.recording_status == RecordingStatus.RECORDING:
            return

        self.video_processing_pipeline = VideoProcessingPipeline(
            auto_concatenate=bool(self.settings["CONCATENATE_OUTPUTS"]),
            delete=bool(self.settings["DELETE_ORIGINALS"]),
            status_callback=self.status_callback
        )

        # Try to stop previous thread
        if self.listener_thread:
            self.stop_event.set()
            self.listener_thread.join()
            self.stop_event.clear()

        # And start again
        self.listener_thread = threading.Thread(
            target=run,
            args=(
                self.settings,
                self.status_callback,
                self.stop_event,
                self.video_processing_pipeline
            )
        )
        self.listener_thread.start()

    def run_concatenate(self, event=None):
        self.video_processing_pipeline.concatenate_candidates_in_thread()

    def status_callback(self, message):
        """update the internal status based on a status message and update ui"""

        # Do logging
        if type(message) is tuple and (message[0] == ProcessingStatusCallback.PROCESSING_ERROR or message[
            0] == RecordingStatusCallback.RECORDING_ERROR):
            try:
                logger.error(f"Got error status message: {message}", exc_info=message[1])
            except Exception:
                logger.error(f"Got error status message, error could not be parsed: {message}", exc_info=True)
        elif message == ProcessingStatusCallback.PROCESSING_ERROR or message == RecordingStatusCallback.RECORDING_ERROR:
            logger.error(f"Got error status message {message} (without more details).")
        else:
            logger.info(f"Got status message: {message}.")

        # Parse error message into internal state
        if message == RecordingStatusCallback.RECORDING_READY:
            self.recording_status = RecordingStatus.READY
        elif message == RecordingStatusCallback.RECORDING_STARTED:
            self.recording_status = RecordingStatus.RECORDING
        elif message == RecordingStatusCallback.RECORDING_ENDED:
            self.recording_status = RecordingStatus.READY
        elif type(message) is tuple and message[0] == RecordingStatusCallback.RECORDING_ERROR:
            self.recording_status = RecordingStatus.ERROR
            self.error_message = message[1:]

        elif message == ProcessingStatusCallback.PROCESSING_READY:
            self.processing_status = ProcessingStatus.READY
        elif message == ProcessingStatusCallback.PROCESSING_STARTED:
            self.processing_status = ProcessingStatus.PROCESSING
        elif message == ProcessingStatusCallback.PROCESSING_ENDED:
            self.processing_status = ProcessingStatus.READY
        elif type(message) is tuple and message[0] == ProcessingStatusCallback.PROCESSING_ERROR:
            self.processing_status = ProcessingStatus.ERROR
            self.error_message = message[1:]

        self.display_status()

    def display_status(self):
        """look at the internal status and update ui accordingly"""

        # Display output based on internal state
        if self.recording_status == RecordingStatus.ERROR or self.processing_status == ProcessingStatus.ERROR:
            self.icon.icon = Image.open(os.path.join(self.base_path, "data", "gray.ico"))
            color = "red"
            if len(self.error_message) > 0:
                text = f"Error: {self.error_message}"
            else:
                text = "Unknown Error"

        elif self.recording_status == RecordingStatus.INIT or self.processing_status == ProcessingStatus.INIT:
            color = "orange"
            text = "Initializing"
            self.icon.icon = Image.open(os.path.join(self.base_path, "data", "gray.ico"))

        elif self.recording_status == RecordingStatus.READY:
            color = "#33dd33"
            self.icon.icon = Image.open(os.path.join(self.base_path, "data", "orange.ico"))

            if self.processing_status == ProcessingStatus.PROCESSING:
                text = "Ready (and processing previous video)"
            else:
                text = "Ready"

        elif self.recording_status == RecordingStatus.RECORDING:
            color = "green"
            self.icon.icon = Image.open(os.path.join(self.base_path, "data", "green.ico"))

            if self.processing_status == ProcessingStatus.PROCESSING:
                text = "Recording (and processing previous video)"
            else:
                text = "Recording"

        else:
            # Technically all cases should be covered above, having this case just in case.
            logger.warning("Got into a Not Ready state!")
            color = "red"
            text = "Not Ready"
            self.icon.icon = Image.open(os.path.join(self.base_path, "data", "gray.ico"))

        self.status_subframe.configure(fg_color=color)
        self.status_label.configure(text=text)

    def save_settings(self, has_changed=False):
        """save all settings to file if something has changed
        :return true if something has changed"""
        pairs = {
            "OBS_HOST": self.obs_host_entry,
            "OBS_PORT": self.obs_port_entry,
            "OBS_PASSWORD": self.obs_password_entry,
            "LOG_DIR": self.log_directory_entry,
            "OUTPUT_DIR": self.output_directory_entry,
            "TIMEOUT": self.timeout_entry,
            "CONCATENATE_OUTPUTS": self.concatenate_outputs_var,
            "DELETE_ORIGINALS": self.delete_originals_var
        }

        # Check if any entry has changed
        for key, entry in pairs.items():
            if self.settings[key] != entry.get():
                self.settings[key] = entry.get()
                has_changed = True

        # Save if anything did change
        if has_changed:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.info("Saved Settings")

        return has_changed

    def exit(self, icon=None):
        """close all threads and exit the program"""
        logger.info("Exiting...")

        # Stop tray icon (if we are given an icon we are in that thread and don't need to join it)
        self.icon.stop()
        if icon is None:
            self.tray_thread.join()

        # Stop Listener
        self.stop_event.set()
        self.listener_thread.join()

        self.root.destroy()

    def minimize_to_tray(self, event=None):
        """close main window"""
        # Workaround to ensure function is only called once
        if self.is_minimized:
            return
        self.is_minimized = True

        logger.info("Minimizing to Tray")

        # Clear main window
        self.root.withdraw()

    def show_from_tray(self, icon=None):
        """open main window"""
        logger.info("Maximizing from Tray")

        # Build main window
        self.root.deiconify()

        # Workaround to ensure minimize function is not called when showing again
        self.root.after(0, self.reset_minimized)

    def reset_minimized(self, event=None):
        """callback function for show_from_tray()"""
        self.is_minimized = False


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = FightRecorderApp(root)
    root.mainloop()
