"""
video_processing.py
FFmpeg-based video probing and key-frame extraction for golf swing analysis.
"""

import os
import uuid
from typing import Dict

import ffmpeg


def get_video_duration_seconds(video_path: str) -> float:
    """Return the duration of *video_path* in seconds using ffmpeg.probe."""
    try:
        probe = ffmpeg.probe(video_path)
    except ffmpeg.Error as exc:
        raise RuntimeError(
            f"ffmpeg could not probe the video file: {exc.stderr}"
        ) from exc

    # Try the container-level duration first, then fall back to the first
    # video stream's duration.
    duration_str = probe.get("format", {}).get("duration")
    if duration_str is None:
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video" and "duration" in stream:
                duration_str = stream["duration"]
                break

    if duration_str is None:
        raise RuntimeError(
            "Could not determine video duration from ffmpeg probe output."
        )

    return float(duration_str)


def extract_frame_at_time(
    video_path: str,
    timestamp: float,
    output_dir: str,
) -> str:
    """Extract a single PNG frame at *timestamp* seconds and save it to *output_dir*.

    Returns the absolute path to the extracted PNG file.
    """
    frame_filename = f"{uuid.uuid4().hex}.png"
    frame_path = os.path.join(output_dir, frame_filename)

    try:
        (
            ffmpeg
            .input(video_path, ss=timestamp)
            .output(frame_path, vframes=1, format="image2", vcodec="png")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        raise RuntimeError(
            f"ffmpeg failed to extract frame at {timestamp:.2f}s: {exc.stderr}"
        ) from exc

    if not os.path.isfile(frame_path):
        raise RuntimeError(
            f"Frame file was not created at {frame_path}."
        )

    return frame_path


def extract_swing_key_frames(
    video_path: str,
    output_dir: str,
) -> Dict[str, str]:
    """Extract three key swing frames (setup, top of backswing, impact).

    Returns a dict mapping phase name → frame file path.
    """
    duration = get_video_duration_seconds(video_path)

    if duration <= 0:
        raise RuntimeError("Video duration is zero or negative.")

    setup_t = max(duration * 0.10, 0.0)
    top_t = duration * 0.50
    impact_t = duration * 0.63

    frames: Dict[str, str] = {}
    for phase, timestamp in [
        ("setup", setup_t),
        ("top", top_t),
        ("impact", impact_t),
    ]:
        frames[phase] = extract_frame_at_time(video_path, timestamp, output_dir)

    return frames
