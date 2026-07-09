from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .media_probe_tool import probe_media
from .segment_export_tool import resolve_ffmpeg


def generate_final_review(clips: list[dict[str, Any]], output_path: str, temp_dir: str) -> dict[str, Any]:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return {"success": False, "backend": "ffmpeg_concat", "error": "ffmpeg unavailable"}
    output = Path(output_path)
    root = output.parent
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "final_video_ffmpeg.log"
    normalized_dir = root / "assets" / "normalized_segments"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    temp = Path(temp_dir)
    temp.mkdir(parents=True, exist_ok=True)

    normalized = []
    stderr_parts: list[str] = []
    for idx, clip in enumerate(clips, start=1):
        source = Path(clip["export_path"])
        normalized_path = normalized_dir / f"normalized_segment_{idx:03}.mp4"
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-vf",
            "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(normalized_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        stderr_parts.append(f"\n--- normalize {idx} ---\nCOMMAND: {' '.join(command)}\n{completed.stderr}\n{completed.stdout}")
        probe = probe_media(str(normalized_path))
        if completed.returncode != 0 or not probe.get("visual_valid"):
            log_path.write_text("\n".join(stderr_parts), encoding="utf-8", errors="ignore")
            return {"success": False, "backend": "ffmpeg_concat", "error": f"normalized segment {idx} failed media probe", "output_path": str(output), "data": {"ffmpeg_log_path": str(log_path), "failed_probe": probe}}
        clip["normalized_export_path"] = str(normalized_path)
        normalized.append(normalized_path.resolve())

    concat = temp / "concat_list.txt"
    concat.write_text("\n".join(f"file '{path.as_posix()}'" for path in normalized), encoding="utf-8")
    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    stderr_parts.append(f"\n--- final concat ---\nCOMMAND: {' '.join(command)}\n{completed.stderr}\n{completed.stdout}")
    log_path.write_text("\n".join(stderr_parts), encoding="utf-8", errors="ignore")
    if completed.returncode != 0 or not output.exists() or output.stat().st_size <= 0:
        return {"success": False, "backend": "ffmpeg_concat", "error": completed.stderr[-1200:], "output_path": str(output), "data": {"ffmpeg_log_path": str(log_path)}}
    probe = probe_media(str(output))
    if not probe.get("visual_valid"):
        return {"success": False, "backend": "ffmpeg_concat", "error": "final_review failed visual media probe", "output_path": str(output), "data": {"ffmpeg_log_path": str(log_path), "final_probe": probe}}
    return {
        "success": True,
        "backend": "ffmpeg_concat",
        "output_path": str(output),
        "data": {
            "duration": probe.get("duration", 0.0),
            "has_audio": probe.get("has_audio", False),
            "segment_count": len(clips),
            "normalized_segments_used": True,
            "normalized_dir": str(normalized_dir),
            "ffmpeg_log_path": str(log_path),
            "final_probe": probe,
        },
    }


def probe_duration(ffmpeg: str, path: str) -> float:
    completed = subprocess.run([ffmpeg, "-i", path], capture_output=True, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", completed.stderr + completed.stdout)
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)


def probe_has_audio(ffmpeg: str, path: str) -> bool:
    completed = subprocess.run([ffmpeg, "-i", path], capture_output=True, text=True)
    return "Audio:" in (completed.stderr + completed.stdout)

