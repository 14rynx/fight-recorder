import json

import customtkinter as ctk

from runner import run


class SettingsApp:
    def __init__(self, root):
        # Main
        self.root = root
        self.root.title("Fight Recorder")

        self.settings_file = 'settings.json'
        self.load_settings()

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

        self.status_subframe = ctk.CTkFrame(master=self.status_frame, fg_color="red")
        self.status_subframe.grid(row=1, column=0, sticky='wne', padx=10, pady=5)

        self.status_label = ctk.CTkLabel(self.status_subframe, text="Not implemented.")
        self.status_label.grid(row=1, column=0, sticky='we')

        self.run()

    def select_log_directory(self):
        directory = ctk.filedialog.askdirectory()
        self.log_directory.set(directory)

    def select_output_directory(self):
        directory = ctk.filedialog.askdirectory()
        self.output_directory.set(directory)

    def set_startup(self):
        raise NotImplementedError

        """ 
        Something like this:
        from os import getcwd
        from shutil import copy
        copy(getcwd() + '/settings.exe', 'C:/Users/USERNAME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup')
        """

    def load_settings(self):
        try:
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {}

    def save_and_run(self, event=None):
        self.save_settings()
        self.run()

    def run(self, event=None):
        try:
            run(self.settings)
        except Exception as e:
            self.set_status("red", f"Error: {e}")

    def save_settings(self, event=None):
        self.settings['OBS_HOST'] = self.obs_host_entry.get()
        self.settings['OBS_PORT'] = self.obs_port_entry.get()
        self.settings['OBS_PASSWORD'] = self.obs_password_entry.get()

        self.settings['LOG_DIR'] = self.log_directory_entry.get()
        self.settings['OUTPUT_DIR'] = self.output_directory_entry.get()

        self.settings['TIMEOUT'] = self.timeout_entry.get()
        self.settings['CONCATENATE_OUTPUTS'] = self.concatenate_outputs_var.get()
        self.settings['DELETE_ORIGINALS'] = self.delete_originals_var.get()

        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def set_status(self, color, text):
        self.status_subframe.configure(fg_color=color)
        self.status_label.configure(text=text)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = SettingsApp(root)
    root.mainloop()
