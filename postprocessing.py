import os
import threading

from moviepy.editor import VideoFileClip, concatenate_videoclips


class PostProcessing:
    def __init__(self, concatenate=True, delete=False):
        self.concatenate = concatenate
        self.delete = delete

    def process(self, replay_path, recording_path, output_dir, output_name):

        destination_replay = os.path.join(output_dir, f"{output_name}_replay.mkv")
        destination_recording = os.path.join(output_dir, f"{output_name}_recording.mkv")
        destination_concatenated = os.path.join(output_dir, f"{output_name}_concatenated.mkv")

        # Move files
        os.rename(replay_path, destination_replay)
        os.rename(recording_path, destination_recording)

        # Concatenate (and delete if needed)
        if self.concatenate:
            video_processing_thread = threading.Thread(
                target=process_video_clips,
                args=(
                    destination_replay,
                    destination_recording,
                    destination_concatenated,
                    self.delete
                )
            )
            video_processing_thread.start()


def process_video_clips(replay_path, recording_path, output_path, delete=False):
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
