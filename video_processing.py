import os
import threading
import time
from enum import Enum
import subprocess
import sys

class ProcessingStatusCallback(Enum):
    PROCESSING_READY = 1
    PROCESSING_STARTED = 2
    PROCESSING_ENDED = 3
    PROCESSING_ERROR = 4


class ProcessingElement:
    def __init__(self, replay_path, recording_path, output_dir, output_name):
        self.replay_path = replay_path
        self.recording_path = recording_path
        self.output_dir = output_dir
        self.output_name = output_name
        self.renamed = False

    @property
    def extension(self):
        _, extension = os.path.splitext(self.replay_path)
        return extension

    @property
    def replay_destination(self):
        return os.path.join(self.output_dir, f"{self.output_name}_replay{self.extension}").replace("\\", "/")

    @property
    def recording_destination(self):
        return os.path.join(self.output_dir, f"{self.output_name}_recording{self.extension}").replace("\\", "/")

    @property
    def concatenated_destination(self):
        return os.path.join(self.output_dir, f"{self.output_name}_concatenated{self.extension}").replace("\\", "/")


class VideoProcessingPipeline:
    def __init__(self, auto_concatenate, delete, status_callback, logger, files_path, **kwargs):
        self.auto_concatenate = auto_concatenate
        self.delete = delete
        self.status_callback = status_callback
        self.logger = logger
        self.files_path = files_path

        self.concatenate_candidate_elements = []
        self.status_callback(ProcessingStatusCallback.PROCESSING_READY)

    def process(self, replay_path, recording_path, output_dir, output_name):
        video_element = ProcessingElement(replay_path, recording_path, output_dir, output_name)

        if self.auto_concatenate:
            self.concatenate_in_thread(video_element)
            if not self.delete:
                self.rename_in_thread(video_element)
        else:
            self.rename_in_thread(video_element)
            self.concatenate_candidate_elements.append(video_element)

    def rename(self, video_element):
        if os.path.exists(video_element.replay_path):
            os.rename(video_element.replay_path, video_element.replay_destination)

        if os.path.exists(video_element.recording_path):
            # File still in use by OBS
            while True:
                try:
                    os.rename(video_element.recording_path, video_element.recording_destination)
                    break
                except PermissionError:
                    time.sleep(10)

    def rename_in_thread(self, video_element):
        rename_thread = threading.Thread(target=self.rename, args=(video_element,))
        rename_thread.start()

    def concatenate(self, video_element):
        self.status_callback(ProcessingStatusCallback.PROCESSING_STARTED)

        concat_directory = os.path.join(self.files_path, "concat.txt")

        if video_element.renamed:
            replay_input = video_element.replay_destination
            recording_input = video_element.recording_destination
        else:
            replay_input = video_element.replay_path
            recording_input = video_element.recording_path

        try:
            with open(concat_directory, 'w') as concat_file:
                if not os.path.exists(replay_input) or \
                        not os.path.exists(recording_input):
                    self.logger.error("Could not start processing because input files did not exist!")
                    return

                concat_file.writelines([
                    f"file '{replay_input}'\n",
                    f"file '{recording_input}'"
                ])

            command = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_directory,
                "-c", "copy",
                video_element.concatenated_destination
            ]

            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flags
            )

            _, stderr = process.communicate()
            if process.returncode != 0:
                self.status_callback((ProcessingStatusCallback.PROCESSING_ERROR, stderr))
                return

            os.remove(concat_directory)

            if self.delete:
                os.remove(replay_input)
                os.remove(recording_input)

            self.status_callback(ProcessingStatusCallback.PROCESSING_ENDED)
        except Exception as e:
            self.status_callback((ProcessingStatusCallback.PROCESSING_ERROR, e))

    def concatenate_in_thread(self, video_element):
        video_processing_thread = threading.Thread(target=self.concatenate, args=(video_element,))
        video_processing_thread.start()

    def concatenate_candidates(self, concatenate_candidate_elements):
        for video_element in concatenate_candidate_elements:
            self.concatenate(video_element)

    def concatenate_candidates_in_thread(self):
        video_processing_thread = threading.Thread(
            target=self.concatenate_candidates,
            args=(self.concatenate_candidate_elements,)
        )
        video_processing_thread.start()
