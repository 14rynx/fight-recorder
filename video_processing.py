import logging
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
    def __init__(self, concatenate, delete, status_callback, codec="libx264", audio_codec="aac", threads=8):
        self.concatenate = concatenate
        self.delete = delete
        self.status_callback = status_callback
        self.codec = codec
        self.audio_codec = audio_codec
        self.threads = threads
        self.status_callback(ProcessingStatusCallback.PROCESSING_READY)

    def process(self, replay_path, recording_path, output_dir, output_name):

        _, extension = os.path.splitext(replay_path)

        destination_replay = os.path.join(output_dir, f"{output_name}_replay{extension}")
        destination_recording = os.path.join(output_dir, f"{output_name}_recording{extension}")
        destination_concatenated = os.path.join(output_dir, f"{output_name}_concatenated{extension}")

        if os.path.exists(replay_path):
            os.rename(replay_path, destination_replay)

        if os.path.exists(recording_path):
            while True:
                try:
                    os.rename(recording_path, destination_recording)
                    break
                except PermissionError:  # File still in use by OBS
                    time.sleep(10)

        # Concatenate (and delete if needed)
        if self.concatenate and os.path.exists(destination_replay) and os.path.exists(destination_recording):
            video_processing_thread = threading.Thread(
                target=self.processing_thread,
                args=(
                    destination_replay,
                    destination_recording,
                    destination_concatenated,
                )
            )
            video_processing_thread.start()

    def processing_thread(self, replay_path, recording_path, output_path):
        self.status_callback(ProcessingStatusCallback.PROCESSING_STARTED)

        try:
            # Load video clips
            replay_buffer_clip = VideoFileClip(replay_path)
            recording_clip = VideoFileClip(recording_path)

            # Concatenate video clips
            combined_clip = concatenate_videoclips([replay_buffer_clip, recording_clip])

            combined_clip.write_videofile(output_path, codec=self.codec, audio_codec=self.audio_codec,
                                          threads=self.threads, logger=None)

            # Close the video clips
            replay_buffer_clip.close()
            recording_clip.close()

            if self.delete:
                os.remove(replay_path)
                os.remove(recording_path)

            self.status_callback(ProcessingStatusCallback.PROCESSING_ENDED)
        except Exception as e:
            self.status_callback((ProcessingStatusCallback.PROCESSING_ERROR, e))
