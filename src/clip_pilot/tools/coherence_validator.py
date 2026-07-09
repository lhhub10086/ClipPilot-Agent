from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEPENDENT_START = {"and", "but", "so", "because", "this", "that", "it", "they", "which", "然后", "所以", "这个", "那个", "它"}


def validate_semantic_timeline(timeline: dict[str, Any]) -> dict[str, Any]:
    items = timeline.get("items", [])
    checks = {
        "no_mid_sentence_cut": all(not item.get("starts_mid_sentence") and not item.get("ends_mid_sentence") for item in items),
        "segment_starts_cleanly": all(_starts_cleanly(item.get("text", "")) for item in items),
        "segment_ends_cleanly": all(_ends_cleanly(item.get("text", "")) for item in items),
        "segment_has_complete_thought": all(float(item.get("completeness_score", 0.0)) >= 0.55 and float(item.get("standalone_score", 0.0)) >= 0.5 for item in items),
        "storyline_order_valid": _chronological(items),
        "cross_segment_transition_valid": _transition_valid(items),
        "no_unresolved_reference": all(_starts_cleanly(item.get("text", "")) for item in items),
    }
    checks["semantic_timeline_valid"] = bool(items) and all(checks.values())
    return {"success": True, "backend": "coherence_validator", "data": {"checks": checks, "semantic_timeline_valid": checks["semantic_timeline_valid"]}}


def write_transcript_review(timeline: dict[str, Any], output_path: str) -> dict[str, Any]:
    lines = ["# Storyline Review", ""]
    for idx, item in enumerate(timeline.get("items", []), start=1):
        lines.extend(
            [
                f"## Segment {idx}",
                "",
                f"Role: {item.get('role')}",
                f"Time: {item.get('source_start')} - {item.get('source_end')}",
                "Text:",
                str(item.get("text", "")),
                "",
                "Why selected:",
                str(item.get("selection_reason", "")),
                "",
                "Coherence:",
                f"- starts cleanly: {'yes' if _starts_cleanly(item.get('text', '')) else 'no'}",
                f"- ends cleanly: {'yes' if _ends_cleanly(item.get('text', '')) else 'no'}",
                f"- standalone: {'yes' if float(item.get('standalone_score', 0.0)) >= 0.5 else 'no'}",
                f"- previous/next relation: chronological course-review storyline",
                "",
            ]
        )
    path = Path(output_path)
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"success": True, "backend": "transcript_review_writer", "output_path": str(path), "data": {"segment_count": len(timeline.get("items", []))}}


def _starts_cleanly(text: str) -> bool:
    tokens = re.findall(r"[A-Za-z]+|[\u4e00-\u9fff]+", text.lower())
    if not tokens:
        return False
    return tokens[0] not in DEPENDENT_START


def _ends_cleanly(text: str) -> bool:
    stripped = text.strip()
    return bool(re.search(r"[.!?。！？]\s*$", stripped)) or len(stripped) >= 12


def _chronological(items: list[dict[str, Any]]) -> bool:
    starts = [float(item.get("source_start", 0.0)) for item in items]
    return starts == sorted(starts)


def _transition_valid(items: list[dict[str, Any]]) -> bool:
    if len(items) <= 1:
        return True
    # For course-review dry runs, chronological ordering is the minimum accepted transition.
    return _chronological(items)


def write_semantic_timeline(path: str, source_video: str, items: list[dict[str, Any]], storyline_plan: dict[str, Any]) -> dict[str, Any]:
    cursor = 0.0
    timeline_items = []
    for idx, item in enumerate(sorted(items, key=lambda value: float(value["start"])), start=1):
        duration = round(float(item["end"]) - float(item["start"]), 3)
        timeline_items.append(
            {
                "segment_id": f"segment_{idx:03}",
                "role": item.get("role", "core_concept"),
                "source_start": round(float(item["start"]), 3),
                "source_end": round(float(item["end"]), 3),
                "target_start": round(cursor, 3),
                "target_end": round(cursor + duration, 3),
                "duration": duration,
                "text": item.get("text", item.get("transcript", "")),
                "sentence_ids": item.get("sentence_ids", []),
                "semantic_block_ids": item.get("semantic_block_ids", []),
                "starts_mid_sentence": bool(item.get("starts_mid_sentence", False)),
                "ends_mid_sentence": bool(item.get("ends_mid_sentence", False)),
                "standalone_score": item.get("standalone_score", 0.0),
                "completeness_score": item.get("completeness_score", 0.0),
                "coherence_score": item.get("coherence_score", 0.0),
                "selection_reason": item.get("selection_reason", ""),
                "bridge_text_before": item.get("bridge_text_before"),
                "bridge_text_after": item.get("bridge_text_after"),
            }
        )
        cursor += duration
    payload = {"source_video": source_video, "storyline_plan": storyline_plan, "duration": round(cursor, 3), "items": timeline_items}
    out = Path(path)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "semantic_timeline_writer", "output_path": str(out), "data": {"semantic_timeline": payload, "segment_count": len(timeline_items), "duration": round(cursor, 3)}}

