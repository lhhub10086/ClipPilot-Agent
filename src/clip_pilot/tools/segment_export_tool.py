from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .media_probe_tool import probe_media


def resolve_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def export_segments(video_path: str, clips: list[dict[str, Any]], output_dir: str, add_boundary_fade: bool = False) -> dict[str, Any]:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return {"success": False, "backend": "ffmpeg", "error": "ffmpeg unavailable"}
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    exported = []
    valid_clips = []
    original_count = len(clips)
    source_probe = probe_media(video_path, sample_frames=30)
    for idx, clip in enumerate(clips, start=1):
        path = out / f"selected_segment_{idx:03}.mp4"
        duration = max(0.1, float(clip["end"]) - float(clip["start"]))
        command = [
            ffmpeg,
            "-y",
            "-ss",
            str(clip["start"]),
            "-i",
            video_path,
            "-t",
            str(duration),
        ]
        vf = "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p"
        command.extend(
            [
                "-vf",
                vf,
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
                str(path),
            ]
        )
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0 or not path.exists() or path.stat().st_size <= 0:
            return {"success": False, "backend": "ffmpeg", "error": completed.stderr[-1000:]}
        probe = probe_media(str(path))
        expected_frames = duration * max(float(probe.get("fps") or 24), 1.0) * 0.8
        visual_valid = bool(probe.get("visual_valid")) and int(probe.get("frame_count") or 0) >= expected_frames
        duration_valid = abs(float(probe.get("duration") or 0) - duration) <= max(1.0, duration * 0.15)
        audio_valid = (not source_probe.get("has_audio")) or bool(probe.get("has_audio"))
        if not (visual_valid and duration_valid and audio_valid):
            clip["export_probe"] = probe
            clip["export_rejected"] = True
            continue
        clip["export_path"] = str(path)
        clip["asset_path"] = f"assets/selected_segments/{path.name}"
        clip["export_probe"] = probe
        valid_clips.append(clip)
        exported.append({"clip_id": clip["clip_id"], "path": str(path), "bytes": path.stat().st_size, "probe": probe})
    clips[:] = valid_clips
    if not exported:
        return {"success": False, "backend": "ffmpeg", "error": "all selected segments failed media validation"}
    return {
        "success": True,
        "backend": "ffmpeg_reencode",
        "data": {
            "clips": exported,
            "segment_count": len(exported),
            "boundary_fade": False,
            "source_probe": source_probe,
            "rejected_count": original_count - len(exported),
        },
    }

