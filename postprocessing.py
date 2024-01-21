import os
import threading
import time

from moviepy.editor import VideoFileClip, concatenate_videoclips


class PostProcessing:
    def __init__(self, concatenate, delete, status_callback):
        self.concatenate = concatenate
        self.delete = delete
        self.status_callback = status_callback

    def process(self, replay_path, recording_path, output_dir, output_name):
        self.status_callback("processing_start")

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
                target=process_video_clips,
                args=(
                    destination_replay,
                    destination_recording,
                    destination_concatenated,
                    self.delete,
                    self.status_callback
                )
            )
            video_processing_thread.start()


def process_video_clips(replay_path, recording_path, output_path, delete, status_callback):
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

    status_callback("processing_end")
