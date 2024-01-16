import datetime
import os
import re
import time
import obsws_python as obs
from dotenv import load_dotenv

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
    def __init__(self, host, port, password):
        self.ws = obs.ReqClient(host=host, port=port, password=password, timeout=3)
        self.timeout = None

    def start(self):
        if self.timeout is None:
            try:
                self.ws.start_record()
                self.ws.save_replay_buffer()
                print(self.ws.get_last_replay_buffer_replay())
                self.timeout = datetime.datetime.now() + datetime.timedelta(seconds=60)
            except Exception as e:
                print(f"Error starting recording: {e}")
            else:
                print("Started Recording")

    def check_timeout(self):
        if self.timeout is not None and self.timeout < datetime.datetime.now():
            self.ws.stop_record()
            self.timeout = None
            print("Ended Recording")

    def set_timeout(self):
        if self.timeout is not None:
            self.timeout = datetime.datetime.now() + datetime.timedelta(seconds=60)


def check_log_content(log_content):
    print(log_content)
    for regex_name, value in compiled_regexes.items():
        if len(extract(value, log_content)) > 0:
            return True
    return False


def extract(regex, log_content):
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
    with open(file_path, 'r') as file:
        file.seek(last_position)
        new_content = file.read()
        new_position = file.tell()

    return new_content, new_position


def monitor_directory(directory_path, timeout_recorder):
    observed_files = {}

    # Skip existing files on startup
    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)
        observed_files[file_path] = os.path.getsize(file_path)

    # Search for new files and read them slowly
    while True:
        for file_name in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file_name)

            last_position = observed_files.get(file_path, 0)
            new_content, new_position = read_log_file(file_path, last_position)

            if new_content:
                if check_log_content(new_content):
                    timeout_recorder.start()
                    timeout_recorder.set_timeout()

                observed_files[file_path] = new_position

        timeout_recorder.check_timeout()

        time.sleep(1)  # Adjust the sleep interval as needed


if __name__ == "__main__":
    timeout_recorder = TimeoutRecording(
        host=os.environ["OBS_HOST"],
        port=int(os.environ["OBS_PORT"]),
        password=os.environ["OBS_PASSWORD"]
    )

    monitor_directory(
        directory_path=os.environ["LOG_DIRECTORY"],
        timeout_recorder=timeout_recorder
    )
