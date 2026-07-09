from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def probe_media(path: str, sample_frames: int = 60) -> dict[str, Any]:
    media = Path(path)
    result: dict[str, Any] = {
        "path": str(media),
        "exists": media.exists(),
        "file_size": media.stat().st_size if media.exists() else 0,
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "frame_count": 0,
        "has_audio": False,
        "video_codec": "",
        "audio_codec": "",
        "black_frame_ratio": 1.0,
        "non_black_frame_ratio": 0.0,
        "first_valid_frame_time": None,
        "last_valid_frame_time": None,
        "valid_visual_duration_estimate": 0.0,
        "visual_valid": False,
        "backend": "media_probe",
        "warnings": [],
    }
    if not media.exists() or media.stat().st_size <= 0:
        return result
    result.update(_probe_with_ffmpeg(str(media)))
    result.update(_probe_frames_with_opencv(str(media), sample_frames))
    result["non_black_frame_ratio"] = round(1.0 - float(result["black_frame_ratio"]), 4)
    min_frames = max(1, int(float(result["duration"]) * max(float(result["fps"]), 1.0) * 0.5))
    result["visual_valid"] = (
        int(result["frame_count"]) >= min_frames
        and int(result["width"]) > 0
        and int(result["height"]) > 0
        and float(result["fps"]) > 0
        and float(result["black_frame_ratio"]) < 0.5
    )
    return result


def _probe_with_ffmpeg(path: str) -> dict[str, Any]:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return {"warnings": ["ffmpeg_unavailable_for_probe"]}
    try:
        completed = subprocess.run([ffmpeg, "-i", path], capture_output=True, text=True, timeout=30)
    except Exception as exc:
        return {"warnings": [f"ffmpeg_probe_failed: {exc}"]}
    text = completed.stderr + completed.stdout
    data: dict[str, Any] = {}
    duration = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if duration:
        hours, minutes, seconds = duration.groups()
        data["duration"] = round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)
    video = re.search(r"Video:\s*([^,\s]+).*?,\s*(\d+)x(\d+).*?,\s*([\d.]+)\s*fps", text)
    if video:
        data["video_codec"] = video.group(1)
        data["width"] = int(video.group(2))
        data["height"] = int(video.group(3))
        data["fps"] = float(video.group(4))
    audio = re.search(r"Audio:\s*([^,\s]+)", text)
    if audio:
        data["has_audio"] = True
        data["audio_codec"] = audio.group(1)
    return data


def resolve_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _probe_frames_with_opencv(path: str, sample_frames: int) -> dict[str, Any]:
    try:
        import cv2
        import numpy as np
    except Exception as exc:
        return {"warnings": [f"opencv_unavailable_for_frame_probe: {exc}"]}
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return {"warnings": ["opencv_video_open_failed"]}
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = frame_count / fps if fps > 0 and frame_count > 0 else 0.0
    if frame_count <= 0:
        cap.release()
        return {"frame_count": 0, "fps": fps, "width": width, "height": height, "duration": duration, "warnings": ["zero_decoded_frames"]}
    count = max(1, min(sample_frames, frame_count))
    indices = sorted(set(int(round(i * (frame_count - 1) / max(count - 1, 1))) for i in range(count)))
    black = 0
    valid_times: list[float] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            black += 1
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean = float(gray.mean())
        nonzero_ratio = float(np.count_nonzero(gray > 8)) / float(gray.size)
        is_black = mean < 10.0 or nonzero_ratio < 0.02
        if is_black:
            black += 1
        else:
            valid_times.append(idx / fps if fps > 0 else 0.0)
    cap.release()
    black_ratio = black / max(1, len(indices))
    return {
        "frame_count": frame_count,
        "fps": round(fps, 3),
        "width": width,
        "height": height,
        "duration": round(duration, 3),
        "black_frame_ratio": round(black_ratio, 4),
        "first_valid_frame_time": round(valid_times[0], 3) if valid_times else None,
        "last_valid_frame_time": round(valid_times[-1], 3) if valid_times else None,
        "valid_visual_duration_estimate": round(max(valid_times) - min(valid_times), 3) if len(valid_times) > 1 else 0.0,
    }


def write_probe(path: str, output_path: str) -> dict[str, Any]:
    probe = probe_media(path)
    Path(output_path).write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
    return probe

