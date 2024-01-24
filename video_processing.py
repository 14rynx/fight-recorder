import os
import threading
import time

from moviepy.editor import VideoFileClip, concatenate_videoclips

from enum import Enum


class ProcessingStatusCallback(Enum):
    PROCESSING_READY = 1
    PROCESSING_STARTED = 2
    PROCESSING_ENDED = 3
    PROCESSING_ERROR = 4


class VideoProcessing:
    def __init__(self, concatenate, delete, status_callback):
        self.concatenate = concatenate
        self.delete = delete
        self.status_callback = status_callback
        self.status_callback(ProcessingStatusCallback.PROCESSING_READY)

    def process(self, replay_path, recording_path, output_dir, output_name):

        destination_replay = os.path.join(output_dir, f"{output_name}_replay.mkv")
        destination_recording = os.path.join(output_dir, f"{output_name}_recording.mkv")
        destination_concatenated = os.path.join(output_dir, f"{output_name}_concatenated.mkv")

        os.rename(replay_path, destination_replay)
        while True:
            try:
                os.rename(recording_path, destination_recording)
                break
            except PermissionError:  # File in use by OBS
                time.sleep(10)

        # Concatenate (and delete if needed)
        if self.concatenate:
            video_processing_thread = threading.Thread(
                target=processing_thread,
                args=(
                    destination_replay,
                    destination_recording,
                    destination_concatenated,
                    self.delete,
                    self.status_callback
                )
            )
            video_processing_thread.start()


def processing_thread(replay_path, recording_path, output_path, delete, status_callback):
    status_callback(ProcessingStatusCallback.PROCESSING_STARTED)

    try:
        # Load video clips
        replay_buffer_clip = VideoFileClip(replay_path)
        recording_clip = VideoFileClip(recording_path)

        # Concatenate video clips
        combined_clip = concatenate_videoclips([replay_buffer_clip, recording_clip])

        combined_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", threads=8)

        # Close the video clips
        replay_buffer_clip.close()
        recording_clip.close()

        if delete:
            os.remove(replay_path)
            os.remove(recording_path)

        status_callback(ProcessingStatusCallback.PROCESSING_ENDED)
    except Exception as e:
        print(e)
        status_callback(ProcessingStatusCallback.PROCESSING_ERROR)
