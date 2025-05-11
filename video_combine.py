import os
import re
import subprocess
import threading

import customtkinter as ctk


def extract_timestamp(filename):
    match = re.search(r'(\d{8}-\d{6})', os.path.basename(filename))
    return match.group(1) if match else ''


def run_ffmpeg(cmd):
    subprocess.run(cmd, check=True)

def combine_in_thread():
    rename_thread = threading.Thread(target=combine)
    rename_thread.start()

def combine():
    # === File selection ===
    video_files = ctk.filedialog.askopenfilenames(
        title="Select Video Clips",
        filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi")]
    )
    if not video_files:
        print("No files selected. Exiting.")
        exit()

    sorted_files = sorted(video_files, key=extract_timestamp)
    output_file = os.path.splitext(os.path.basename(sorted_files[0]))[0] + "_etc.mkv"
    font_file = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Update if needed

    intermediate_ts_files = []

    # === Generate slides and remux ===
    for i, video in enumerate(sorted_files):
        part_num = i + 1
        slide_path = f"slide_{part_num}.mkv"
        slide_ts = f"slide_{part_num}.ts"
        video_ts = f"video_{part_num}.ts"

        # Generate slide
        cmd_slide = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=2560x1440:d=2:r=60",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-vf", f"drawtext=fontfile={font_file}:text='Part {part_num}':"
                   "fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2",
            "-shortest",
            "-c:v", "libx265",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-t", "2",
            slide_path
        ]
        run_ffmpeg(cmd_slide)

        # Remux slide to TS
        run_ffmpeg([
            "ffmpeg", "-y", "-i", slide_path,
            "-c", "copy", "-bsf:v", "hevc_mp4toannexb",
            "-f", "mpegts", slide_ts
        ])
        intermediate_ts_files.append(slide_ts)

        # Remux video to TS
        run_ffmpeg([
            "ffmpeg", "-y", "-i", video,
            "-c", "copy", "-bsf:v", "hevc_mp4toannexb",
            "-f", "mpegts", video_ts
        ])
        intermediate_ts_files.append(video_ts)

    # === Concatenate TS files ===
    concat_str = "|".join(intermediate_ts_files)
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", f"concat:{concat_str}",
        "-c", "copy",
        "-f", "matroska",
        output_file
    ])

    # === Cleanup ===
    for f in intermediate_ts_files:
        os.remove(f)
    for i in range(1, len(sorted_files) + 1):
        os.remove(f"slide_{i}.mkv")

    print(f"\n✅ Done! Output saved to: {output_file}")
