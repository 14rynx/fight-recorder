import os
import re
import time


class LogReader:
    """Monitor an eve log directory for log changes and return true if something interesting happends"""

    def __init__(self, directory):
        self.directory = directory

        self.regex = re.compile(r'\(combat\)|has applied bonuses to')

        # Figure out current file state
        self.observed_files = {}
        self.file_count = 0
        self.add_new_files(skip=True)

    def add_new_files(self, skip=False):
        """Add check if there are new files and add them to the observed files
        (if they are less than 24h old)"""
        files = os.listdir(self.directory)

        # Check count of files first to save on cpu load
        if len(files) == self.file_count:
            return

        self.file_count = len(files)

        for file_name in files:
            file_path = os.path.join(self.directory, file_name)

            # Only add files that are not already added
            if file_path in self.observed_files:
                continue

            # Only index files which were edited in the last 24 hours to save on cpu load
            if os.path.getmtime(file_path) < time.time() - 24 * 60 * 60:
                continue

            if skip:
                # skip means we should ignore any already existing files ->
                # we add their end to the observed files in case they still get actively written too
                self.observed_files[file_path] = os.path.getsize(file_path)
            else:
                # We add any file from the start
                self.observed_files[file_path] = 0

    def check_log_content(self, log_content):
        """Check if there was something interesting in log content"""

        # Early stop on empty log_content to save on CPU load
        if len(log_content) == 0:
            return False

        return re.search(self.regex, log_content) is not None

    def read_incrementally(self, file_path):
        """Incrementally read a log file based on a known last position and return new content."""

        # Only open the file if it actually changed to not cause extra load
        if os.path.getsize(file_path) > self.observed_files.get(file_path, 0):
            try:

                with open(file_path, 'r', encoding="utf8") as file:
                    file.seek(self.observed_files.get(file_path, 0))
                    new_content = file.read()
                    self.observed_files[file_path] = file.tell()
                return new_content
            except PermissionError:
                return ""
        else:
            return ""

    def check_observed_files(self):
        for file_path in self.observed_files.keys():
            new_content = self.read_incrementally(file_path)
            if self.check_log_content(new_content):
                return True

        return False

    def check_files(self):
        self.add_new_files(skip=False)
        return self.check_observed_files()
