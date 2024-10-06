import os
import threading
import time
from enum import Enum

from moviepy.editor import VideoFileClip, concatenate_videoclips


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

    @property
    def extension(self):
        _, extension = os.path.splitext(self.replay_path)
        return extension

    @property
    def replay_destination(self):
        return os.path.join(self.output_dir, f"{self.output_name}_replay{self.extension}")

    @property
    def recording_destination(self):
        return os.path.join(self.output_dir, f"{self.output_name}_recording{self.extension}")

    @property
    def concatenated_destination(self):
        return os.path.join(self.output_dir, f"{self.output_name}_concatenated{self.extension}")


class VideoProcessingPipeline:
    def __init__(self, auto_concatenate, delete, status_callback, codec="hevc_nvenc", audio_codec="aac",
                 ffmpeg_options=None, threads=8):
        self.auto_concatenate = auto_concatenate
        self.delete = delete
        self.status_callback = status_callback
        self.codec = codec
        self.audio_codec = audio_codec
        if ffmpeg_options is None:
            self.ffmpeg_options = ['-c:v', 'hevc_nvenc', '-rc', 'constqp', '-qp', '16']
        else:
            self.ffmpeg_options = ffmpeg_options
        self.threads = threads

        self.concatenate_candidate_elements = []
        self.status_callback(ProcessingStatusCallback.PROCESSING_READY)

    def process(self, replay_path, recording_path, output_dir, output_name):
        video_element = ProcessingElement(replay_path, recording_path, output_dir, output_name)
        self.rename_in_thread(video_element)

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

        # Continue with concatenate if needed
        if self.auto_concatenate:
            self.concatenate_in_thread(video_element)
        else:
            self.concatenate_candidate_elements.append(video_element)

    def rename_in_thread(self, video_element):
        rename_thread = threading.Thread(target=self.rename, args=(video_element,))
        rename_thread.start()

    def concatenate(self, video_element):
        if os.path.exists(video_element.replay_destination) and os.path.exists(video_element.recording_destination):
            self.status_callback(ProcessingStatusCallback.PROCESSING_STARTED)

            try:
                # Load video clips
                replay_buffer_clip = VideoFileClip(video_element.replay_destination)
                recording_clip = VideoFileClip(video_element.recording_destination)

                # Concatenate video clips
                combined_clip = concatenate_videoclips([replay_buffer_clip, recording_clip])

                combined_clip.write_videofile(
                    video_element.concatenated_destination,
                    codec=self.codec,
                    audio_codec=self.audio_codec,
                    ffmpeg_params=self.ffmpeg_options,
                    threads=self.threads,
                    logger=None
                )

                # Close the video clips
                replay_buffer_clip.close()
                recording_clip.close()

                if self.delete:
                    os.remove(video_element.replay_destination)
                    os.remove(video_element.recording_destination)

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
