from __future__ import annotations

from typing import Any


REQUIRED_CLIP_FIELDS = [
    "clip_id",
    "start",
    "end",
    "title",
    "reason",
    "review_question",
    "clip_suggestion",
    "transcript_evidence",
]


def validate_edit_plan(payload: dict[str, Any]) -> list[str]:
    errors = []
    for key in ["video_path", "subtitle_path", "intent", "selected_clips"]:
        if not payload.get(key):
            errors.append(f"missing {key}")
    clips = payload.get("selected_clips") or []
    if not clips:
        errors.append("selected_clips must be non-empty")
        return errors
    for idx, clip in enumerate(clips, start=1):
        for key in REQUIRED_CLIP_FIELDS:
            if clip.get(key) in (None, ""):
                errors.append(f"clip {idx} missing {key}")
        if float(clip.get("start", 0)) >= float(clip.get("end", 0)):
            errors.append(f"clip {idx} start must be smaller than end")
    return errors


