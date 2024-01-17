import datetime
import os
import re
import threading
import time
import obsws_python as obs
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, concatenate_videoclips

load_dotenv()

# Copied from PELD: https://github.com/ArtificialQualia/PyEveLiveDPS/blob/master/PyEveLiveDPS/logreader.py
# and slightly modified
regexes = {
    'damageOut': "\(combat\) <.*?><b>([0-9]+).*>to<",
    'damageIn': "\(combat\) <.*?><b>([0-9]+).*>from<",
    'armorRepairedOut': "\(combat\) <.*?><b>([0-9]+).*> remote armor repaired to <",
    'hullRepairedOut': "\(combat\) <.*?><b>([0-9]+).*> remote hull repaired to <",
    'shieldBoostedOut': "\(combat\) <.*?><b>([0-9]+).*> remote shield boosted to <",
    'armorRepairedIn': "\(combat\) <.*?><b>([0-9]+).*> remote armor repaired by <",
    'hullRepairedIn': "\(combat\) <.*?><b>([0-9]+).*> remote hull repaired by <",
    'shieldBoostedIn': "\(combat\) <.*?><b>([0-9]+).*> remote shield boosted by <",
    'capTransferedOut': "\(combat\) <.*?><b>([0-9]+).*> remote capacitor transmitted to <",
    'capNeutralizedOut': "\(combat\) <.*?ff7fffff><b>([0-9]+).*> energy neutralized <",
    'nosRecieved': "\(combat\) <.*?><b>\+([0-9]+).*> energy drained from <",
    'capTransferedIn': "\(combat\) <.*?><b>([0-9]+).*> remote capacitor transmitted by <",
    'capNeutralizedIn': "\(combat\) <.*?ffe57f7f><b>([0-9]+).*> energy neutralized <",
    'nosTaken': "\(combat\) <.*?><b>\-([0-9]+).*> energy drained to <",
}

base = '(?:.*ffffffff>(?P<default_pilot>[^\(\)<>]*)(?:\[.*\((?P<default_ship>.*)\)<|<)/b.*> \-(?: (?P<default_weapon>.*?)(?: \-|<)|.*))(?P<pilot>)(?P<ship>)(?P<weapon>)'

# Compile regexes
compiled_regexes = {}
for regex_name, value in regexes.items():
    compiled_regexes[regex_name] = re.compile(value + base)


class TimeoutRecording:
    def __init__(self, host, port, password, timeout=60):
        self.ws = obs.ReqClient(host=host, port=port, password=password, timeout=3)
        self.start_time = None
        self.end_time = None
        self.timeout = timeout

        # Register callback to get information on the current recording path
        self.cl = obs.EventClient(host=host, port=port, password=password)
        self.cl.callback.register(self.on_record_state_changed)
        self.recording_path = None

    def on_record_state_changed(self, data):
        """Callback function, do not rename!"""
        if data.output_path is not None:
            self.recording_path = data.output_path

    @property
    def replay_path(self):
        return self.ws.get_last_replay_buffer_replay().saved_replay_path

    @property
    def output_name(self):
        return self.start_time.strftime("%Y%m%d-%H%M%S")

    def start(self):
        if self.end_time is None:
            try:
                self.ws.start_record()
                self.ws.save_replay_buffer()
                self.end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.timeout)
                self.start_time = datetime.datetime.now()
            except Exception as e:
                print(f"Error starting recording: {e}")
            else:
                print("Started Recording")

    def check_timeout(self):
        if self.end_time is not None and self.end_time < datetime.datetime.now():
            self.ws.stop_record()
            self.end_time = None
            return True

        return False

    def set_timeout(self):
        if self.end_time is not None:
            self.end_time = datetime.datetime.now() + datetime.timedelta(seconds=60)


def process_video_clips(replay_path, recording_path, output_path):
    # Load video clips
    replay_buffer_clip = VideoFileClip(replay_path)
    recording_clip = VideoFileClip(recording_path)

    # Concatenate video clips
    combined_clip = concatenate_videoclips([replay_buffer_clip, recording_clip])

    combined_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", threads=8)

    # Close the video clips
    replay_buffer_clip.close()
    recording_clip.close()
    print(f"Saved clip under {output_path}")


def check_log_content(log_content):
    """Check if there was something interesting in log content"""
    for regex_name, value in compiled_regexes.items():
        if len(extract(value, log_content)) > 0:
            return True
    return False


def extract(regex, log_content):
    """Extract interesting data from log content"""
    return_value = []
    group = regex.finditer(log_content)

    for match in group:
        amount = match.group(1) or 0
        pilot_name = match.group('default_pilot') or match.group('pilot') or '?'
        ship_type = match.group('ship') or match.group('default_ship') or pilot_name
        weapon_type = match.group('default_weapon') or match.group('weapon') or 'Unknown'
        if amount != 0:
            return_group = {'amount': int(amount), 'pilotName': pilot_name.strip(), 'shipType': ship_type,
                            'weaponType': weapon_type}
            return_value.append(return_group)
    return return_value


def read_log_file(file_path, last_position):
    """Incrementally read a log file based on a known last position and return new content."""
    with open(file_path, 'r', encoding="utf8") as file:
        file.seek(last_position)
        new_content = file.read()
        new_position = file.tell()

    return new_content, new_position


def monitor_directory(directory_path, timeout_recorder, concatenated_output_dir=None):
    """Monitor an eve log directory for log changes and make a recording if anything interesting happens"""
    observed_files = {}

    # Figure out current file state
    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        observed_files[file_path] = os.path.getsize(file_path)

    print(f"Observing {directory_path}")

    n = 0

    while True:
        # Search for new files and read them
        for file_name in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file_name)

            last_position = observed_files.get(file_path, 0)
            new_content, new_position = read_log_file(file_path, last_position)

            if new_content:
                if check_log_content(new_content):
                    timeout_recorder.start()
                    timeout_recorder.set_timeout()

                observed_files[file_path] = new_position

        # Check if the recording has ended and display the file paths
        if timeout_recorder.check_timeout():

            print("Ended recording")
            if concatenated_output_dir is not None and concatenated_output_dir != "None":
                # Run the processing function in a separate thread
                video_processing_thread = threading.Thread(
                    target=process_video_clips,
                    args=(
                        timeout_recorder.replay_path,
                        timeout_recorder.recording_path,
                        f"{concatenated_output_dir}\\{timeout_recorder.output_name}.mkv"
                    )
                )
                video_processing_thread.start()
                n += 1

            else:
                print(f"Output files: {timeout_recorder.replay_path} {timeout_recorder.recording_path}")

        time.sleep(1)  # Adjust the sleep interval as needed


if __name__ == "__main__":
    timeout_recorder = TimeoutRecording(
        host=os.environ["OBS_HOST"],
        port=int(os.environ["OBS_PORT"]),
        password=os.environ["OBS_PASSWORD"],
        timeout=int(os.environ["TIMEOUT"])
    )

    monitor_directory(
        directory_path=os.environ["LOG_DIRECTORY"],
        timeout_recorder=timeout_recorder,
        concatenated_output_dir=os.environ["CONCATENATED_OUTPUT"]
    )
