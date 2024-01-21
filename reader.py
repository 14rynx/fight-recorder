import os
import re

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


class LogChecker:
    """Monitor an eve log directory for log changes and return true if something interesting happends"""

    def __init__(self, directory):
        self.directory = directory
        self.observed_files = {}

        # Figure out current file state
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)
            self.observed_files[file_path] = os.path.getsize(file_path)

    def check(self):
        ret = False
        # Search for new files and read them
        for file_name in os.listdir(self.directory):
            file_path = os.path.join(self.directory, file_name)

            last_position = self.observed_files.get(file_path, 0)
            new_content, new_position = read_log_file(file_path, last_position)

            if new_content:
                if check_log_content(new_content):
                    ret = True

                self.observed_files[file_path] = new_position
        return ret
