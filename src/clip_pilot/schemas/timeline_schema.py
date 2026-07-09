from __future__ import annotations

from typing import Any


def build_timeline(source_video: str, final_video: str, clips: list[dict[str, Any]], plan_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    cursor = 0.0
    items = []
    for idx, clip in enumerate(clips, start=1):
        duration = round(float(clip["end"]) - float(clip["start"]), 3)
        items.append(
            {
                "item_id": f"segment_{idx:03}",
                "type": "video_segment",
                "source_start": round(float(clip["start"]), 3),
                "source_end": round(float(clip["end"]), 3),
                "target_start": round(cursor, 3),
                "target_end": round(cursor + duration, 3),
                "duration": duration,
                "title": clip.get("title", ""),
                "review_question": clip.get("review_question", ""),
                "transcript_evidence": clip.get("transcript_evidence", ""),
                "asset_path": clip.get("asset_path", ""),
                "cut_quality_score": clip.get("cut_quality_score", clip.get("score", 0.0)),
                "original_start": clip.get("original_start", clip.get("start")),
                "original_end": clip.get("original_end", clip.get("end")),
                "refined_start": clip.get("refined_start", clip.get("start")),
                "refined_end": clip.get("refined_end", clip.get("end")),
                "boundary_refined": bool(clip.get("boundary_refined", False)),
                "duplicate_ratio": clip.get("duplicate_ratio", 0.0),
                "selection_reason": clip.get("selection_reason", ""),
            }
        )
        cursor += duration
    return {"source_video": source_video, "final_video": final_video, "duration": round(cursor, 3), "plan_policy": plan_policy or {}, "items": items}


def validate_timeline(payload: dict[str, Any]) -> list[str]:
    errors = []
    for key in ["source_video", "final_video", "items"]:
        if not payload.get(key):
            errors.append(f"missing {key}")
    items = payload.get("items") or []
    if not items:
        errors.append("items must be non-empty")
        return errors
    cursor = 0.0
    for idx, item in enumerate(items, start=1):
        for key in ["item_id", "type", "source_start", "source_end", "target_start", "target_end", "duration", "asset_path", "cut_quality_score", "original_start", "original_end", "refined_start", "refined_end", "duplicate_ratio", "selection_reason"]:
            if key not in item:
                errors.append(f"item {idx} missing {key}")
        if float(item.get("source_start", 0)) >= float(item.get("source_end", 0)):
            errors.append(f"item {idx} invalid source range")
        if abs(float(item.get("target_start", 0)) - cursor) > 0.05:
            errors.append(f"item {idx} target timeline is not continuous")
        cursor = float(item.get("target_end", cursor))
    if abs(float(payload.get("duration", cursor)) - cursor) > 0.05:
        errors.append("timeline duration mismatch")
    return errors

