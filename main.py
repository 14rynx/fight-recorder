import contextlib
import json
import os
import sys
import threading

import customtkinter as ctk
import win32com.client

from runner import run


class SettingsApp:
    def __init__(self, root):
        self.stati = ["Initializing"]
        self.stop_event = threading.Event()
        self.listener_thread = None

        # Main
        self.root = root
        self.root.title("Fight Recorder")

        self.settings_path = 'settings.json'
        self.load_settings()

        link_dir = f"{os.environ['APPDATA']}\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        self.link_path = os.path.join(link_dir, "Fight_Recorder.lnk")
        self.bat_path = os.path.join(link_dir, "Fight_Recorder.bat")

        # ---------------------------------------------------------------------
        # OBS Frame
        self.obs_frame = ctk.CTkFrame(master=self.root)
        self.obs_frame.grid(row=0, column=0, padx=10, pady=5, sticky='wne')

        self.obs_frame_title = ctk.CTkLabel(self.obs_frame, text="OBS Settings")
        self.obs_frame_title.grid(row=0, column=0, sticky='w', padx=10, pady=10)

        # OBS Host
        self.obs_host_label = ctk.CTkLabel(self.obs_frame, text="Host:")
        self.obs_host_label.grid(row=1, column=0, sticky='w', padx=10, pady=5)

        self.obs_host_entry = ctk.CTkEntry(self.obs_frame, border_width=0)
        self.obs_host_entry.insert(0, self.settings.get('OBS_HOST', ''))
        self.obs_host_entry.bind('<FocusOut>', self.save_and_run)
        self.obs_host_entry.grid(row=1, column=1, sticky='e', padx=10, pady=5)

        # OBS Port
        self.obs_port_label = ctk.CTkLabel(self.obs_frame, text="Port:")
        self.obs_port_label.grid(row=2, column=0, sticky='w', padx=10, pady=5)

        self.obs_port_entry = ctk.CTkEntry(self.obs_frame, border_width=0)
        self.obs_port_entry.insert(0, self.settings.get('OBS_PORT', ''))
        self.obs_port_entry.bind('<FocusOut>', self.save_and_run)
        self.obs_port_entry.grid(row=2, column=1, sticky='e', padx=10, pady=5)

        # OBS Password
        self.obs_password_label = ctk.CTkLabel(self.obs_frame, text="Password:")
        self.obs_password_label.grid(row=3, column=0, sticky='w', padx=10, pady=5)

        self.obs_password_entry = ctk.CTkEntry(self.obs_frame, show='*', border_width=0)
        self.obs_password_entry.insert(0, self.settings.get('OBS_PASSWORD', ''))
        self.obs_password_entry.bind('<FocusOut>', self.save_and_run)
        self.obs_password_entry.grid(row=3, column=1, sticky='e', padx=10, pady=5)

        # ---------------------------------------------------------------------
        # Behaviour Frame
        self.behaviour_frame = ctk.CTkFrame(master=self.root)
        self.behaviour_frame.grid(row=0, column=1, padx=10, pady=5, sticky='wne')

        self.behaviour_frame_title = ctk.CTkLabel(self.behaviour_frame, text="Behaviour Settings")
        self.behaviour_frame_title.grid(row=0, column=0, sticky='wn', padx=10, pady=10)

        # Timeout
        self.timeout_label = ctk.CTkLabel(self.behaviour_frame, text="Timeout:")
        self.timeout_label.grid(row=1, column=0, sticky='w', padx=10, pady=5)

        self.timeout_entry = ctk.CTkEntry(self.behaviour_frame, border_width=0)
        self.timeout_entry.insert(0, self.settings.get('TIMEOUT', ''))
        self.timeout_entry.bind('<FocusOut>', self.save_and_run)
        self.timeout_entry.grid(row=1, column=1, sticky='e', padx=10, pady=5)

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

        # Delete Originals
        self.delete_originals_var = ctk.BooleanVar()
        self.delete_originals_var.set(self.settings.get('DELETE_ORIGINALS', False))
        self.delete_originals_checkbox = ctk.CTkCheckBox(
            self.behaviour_frame,
            text="Delete original Videos",
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
            command=self.set_startup
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
        self.log_directory_entry = ctk.CTkEntry(self.directory_frame, textvariable=self.log_directory, width=500,
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
        self.output_directory_entry = ctk.CTkEntry(self.directory_frame, textvariable=self.output_directory, width=500,
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
        self.status_frame_title.grid(row=0, column=0, sticky='w', padx=10, pady=10)

        self.status_subframe = ctk.CTkFrame(master=self.status_frame, fg_color="orange")
        self.status_subframe.grid(row=1, column=0, sticky='wne', padx=10, pady=5)

        self.status_label = ctk.CTkLabel(self.status_subframe, text="Initializing")
        self.status_label.grid(row=1, column=0, sticky='we')

        # Start working
        self.get_startup()
        self.run()

    def select_log_directory(self):
        directory = ctk.filedialog.askdirectory()
        self.log_directory.set(directory)
        self.save_and_run()

    def select_output_directory(self):
        directory = ctk.filedialog.askdirectory()
        self.output_directory.set(directory)
        self.save_and_run()

    def get_startup(self):
        # Figure out if the application is ran as a script or not
        if not getattr(sys, 'frozen', False):
            self.run_on_startup_var.set(os.path.exists(self.bat_path))
        else:
            self.run_on_startup_var.set(os.path.exists(self.link_path))

    def set_startup(self):
        if self.run_on_startup_var.get():
            # Figure out if the application is ran as a script or not
            if getattr(sys, 'frozen', False):
                # It is ran as an executable -> Make a shortcut
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(self.link_path)
                shortcut.Targetpath = sys.executable
                shortcut.WorkingDirectory = os.path.dirname(sys.executable)
                shortcut.WindowStyle = 1  # 7 - Minimized, 3 - Maximized, 1 - Normal
                shortcut.save()

            else:
                # It is ran as a script -> Make a bat file to activate venv and start it
                main_file = os.path.realpath(__file__)
                directory = os.path.dirname(main_file)
                command = f"{directory}\\venv\\Scripts\\activate.bat && cd {directory} && start python {main_file}"
                with open(self.bat_path, "w+") as bat_file:
                    bat_file.write(command)

        else:
            # Try removing both kind of link files
            with contextlib.suppress(FileNotFoundError):
                os.remove(self.link_path)
            with contextlib.suppress(FileNotFoundError):
                os.remove(self.bat_path)

    def load_settings(self):
        try:
            with open(self.settings_path, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {}

    def save_and_run(self, event=None):
        changed = self.save_settings()
        if changed:
            self.run()

    def run(self, event=None):
        # Make sure to not kill running recording
        if "Recording..." in self.stati:
            self.set_status("green", "Recording and changing values once done.")
            return

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
                self.stop_event
            )
        )
        self.listener_thread.start()

    def status_callback(self, message):
        print("Got Status Message", message)

        if message == "recording_start":
            self.stati.remove("Ready")
            self.stati.append("Recording...")
        elif message == "recording_end":
            self.stati.remove("Recording...")
            self.stati.append("Ready")

        elif message == "processing_start":
            self.stati.append("Processing...")
        elif message == "processing_end":
            self.stati.remove("Processing...")

        elif message == "recording_ready":
            self.stati = ["Ready"]
        else:
            self.stati = [message]

        # Figure out color
        color = "red"
        if "Ready" in self.stati:
            color = "#33dd33"
        if "Recording..." in self.stati:
            color = "green"
        if "Initializing" in self.stati:
            color = "orange"

        self.set_status(color, ", ".join(self.stati))

    def save_settings(self, event=None):
        has_changed = False

        if self.settings['OBS_HOST'] != self.obs_host_entry.get():
            self.settings['OBS_HOST'] = self.obs_host_entry.get()
            has_changed = True

        if self.settings['OBS_PORT'] != self.obs_port_entry.get():
            self.settings['OBS_PORT'] = self.obs_port_entry.get()
            has_changed = True

        if self.settings['OBS_PASSWORD'] != self.obs_password_entry.get():
            self.settings['OBS_PASSWORD'] = self.obs_password_entry.get()
            has_changed = True

        if self.settings['LOG_DIR'] != self.log_directory_entry.get():
            self.settings['LOG_DIR'] = self.log_directory_entry.get()
            has_changed = True

        if self.settings['OUTPUT_DIR'] != self.output_directory_entry.get():
            self.settings['OUTPUT_DIR'] = self.output_directory_entry.get()
            has_changed = True

        if self.settings['TIMEOUT'] != self.timeout_entry.get():
            self.settings['TIMEOUT'] = self.timeout_entry.get()
            has_changed = True

        if self.settings['CONCATENATE_OUTPUTS'] != self.concatenate_outputs_var.get():
            self.settings['CONCATENATE_OUTPUTS'] = self.concatenate_outputs_var.get()
            has_changed = True

        if self.settings['DELETE_ORIGINALS'] != self.delete_originals_var.get():
            self.settings['DELETE_ORIGINALS'] = self.delete_originals_var.get()
            has_changed = True

        if has_changed:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)

        return has_changed

    def set_status(self, color, text):
        self.status_subframe.configure(fg_color=color)
        self.status_label.configure(text=text)

    def exit(self):
        print("Exiting")
        self.stop_event.set()
        self.listener_thread.join()
        root.destroy()

    # WIP Tray Functionality
    # def exit_from_tray(self, icon):
    #     icon.stop()
    #     self.exit()
    #
    # def minimize_to_tray(self, event=None):
    #     self.root.withdraw()
    #     menu = (pystray.MenuItem('Show', self.show_from_tray),
    #             pystray.MenuItem('Quit', self.exit_from_tray))
    #
    #     # Generate an image and draw a pattern
    #     image = Image.new('RGB', (64, 64), "black")
    #     dc = ImageDraw.Draw(image)
    #     dc.rectangle((32, 0, 64, 32), fill="white")
    #     dc.rectangle((0, 32, 32, 64), fill="white")
    #
    #     icon = pystray.Icon( 'test name', image, "My App", menu)
    #     icon.run()
    #
    # def show_from_tray(self, icon):
    #     icon.stop()
    #     self.root.deiconify()


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = SettingsApp(root)
    root.protocol('WM_DELETE_WINDOW', app.exit)
    root.mainloop()
