from __future__ import annotations

from pathlib import Path
from typing import Any


def write_final_srt(transcript: list[dict[str, Any]], timeline: dict[str, Any], output_path: str) -> dict[str, Any]:
    rows = []
    for item in timeline.get("items", []):
        source_start = float(item["source_start"])
        source_end = float(item["source_end"])
        target_start = float(item["target_start"])
        for seg in transcript:
            if float(seg["end"]) <= source_start or float(seg["start"]) >= source_end:
                continue
            start = max(float(seg["start"]), source_start)
            end = min(float(seg["end"]), source_end)
            rows.append((target_start + start - source_start, target_start + end - source_start, seg["text"]))
    path = Path(output_path)
    lines = []
    for idx, (start, end, text) in enumerate(rows, start=1):
        lines.extend([str(idx), f"{fmt(start)} --> {fmt(end)}", text, ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"success": True, "backend": "timeline_srt", "output_path": str(path), "data": {"subtitle_count": len(rows)}}


def fmt(seconds: float) -> str:
    whole = int(seconds)
    ms = int(round((seconds - whole) * 1000))
    return f"{whole // 3600:02}:{(whole % 3600) // 60:02}:{whole % 60:02},{ms:03}"


