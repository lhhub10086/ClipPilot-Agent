from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def validate_policy(
    *,
    task_plan: dict[str, Any],
    editor_timeline: dict[str, Any],
    transcript_markdown_path: str,
    output_path: str,
    workflow_summary: dict[str, Any] | None = None,
    tolerance_seconds: float = 5.0,
) -> dict[str, Any]:
    report = build_policy_report(
        task_plan=task_plan,
        editor_timeline=editor_timeline,
        transcript_markdown_path=transcript_markdown_path,
        workflow_summary=workflow_summary or {},
        tolerance_seconds=tolerance_seconds,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "policy_validator", "output_path": str(path), "data": report}


def build_policy_report(
    *,
    task_plan: dict[str, Any],
    editor_timeline: dict[str, Any],
    transcript_markdown_path: str = "",
    workflow_summary: dict[str, Any] | None = None,
    tolerance_seconds: float = 5.0,
) -> dict[str, Any]:
    duration_policy = task_plan.get("duration_policy", {})
    count_policy = task_plan.get("segment_count_policy", {})
    items = editor_timeline.get("timeline_items", [])
    final_duration = round(sum(float(item.get("duration", 0.0)) for item in items), 3)
    max_final = float(duration_policy.get("max_final_duration_seconds") or 10**9)
    max_segment = float(duration_policy.get("max_segment_seconds") or 10**9)
    max_segments = int(count_policy.get("max_segments") or 10**9)
    min_segments = int(count_policy.get("min_segments") or 0)
    allow_less = bool(count_policy.get("allow_less_than_target", True))
    intent_text = json.dumps({"task_plan": task_plan, "summary": workflow_summary or {}}, ensure_ascii=False).lower()

    violations: list[dict[str, Any]] = []
    if final_duration > max_final + tolerance_seconds:
        violations.append(_violation("final_duration_exceeds_policy", final_duration, max_final, tolerance_seconds))
    for item in items:
        duration = float(item.get("duration", 0.0))
        if duration > max_segment + tolerance_seconds:
            violations.append(
                {
                    "type": "segment_duration_exceeds_policy",
                    "segment_id": item.get("segment_id"),
                    "actual": round(duration, 3),
                    "limit": max_segment,
                    "tolerance": tolerance_seconds,
                    "severity": "blocking",
                }
            )
    if len(items) > max_segments:
        violations.append(_violation("segment_count_exceeds_policy", len(items), max_segments, 0))
    if len(items) < min_segments and not allow_less:
        violations.append(_violation("segment_count_below_policy", len(items), min_segments, 0))
    if final_duration > max_final + tolerance_seconds:
        violations.append(
            {
                "type": "no_policy_overflow",
                "actual": final_duration,
                "limit": max_final,
                "tolerance": tolerance_seconds,
                "severity": "blocking",
            }
        )

    transcript_words = _transcript_word_count(transcript_markdown_path)
    rough_word_limit = max_final * 3.0
    if transcript_words and transcript_words > rough_word_limit + 100:
        violations.append(
            {
                "type": "transcript_length_exceeds_policy",
                "actual": transcript_words,
                "limit": round(rough_word_limit, 3),
                "tolerance": 100,
                "severity": "blocking",
            }
        )

    if any(term in intent_text for term in ["快速复习", "quick review", "highlight_reel", "highlight reel"]):
        if final_duration > max_final + tolerance_seconds:
            violations.append(
                {
                    "type": "quick_review_too_long",
                    "actual": final_duration,
                    "limit": max_final,
                    "tolerance": tolerance_seconds,
                    "severity": "blocking",
                }
            )

    blocking = [item for item in violations if item.get("severity") == "blocking"]
    return {
        "policy_valid": not blocking,
        "final_duration_seconds": final_duration,
        "max_final_duration_seconds": max_final if max_final < 10**9 else None,
        "max_segment_seconds": max_segment if max_segment < 10**9 else None,
        "selected_segment_count": len(items),
        "violations": violations,
        "recommendation": "proceed" if not blocking else "repair_timeline_reduce_scope",
    }


def _violation(kind: str, actual: float, limit: float, tolerance: float) -> dict[str, Any]:
    return {"type": kind, "actual": actual, "limit": limit, "tolerance": tolerance, "severity": "blocking"}


def _transcript_word_count(path: str) -> int:
    if not path or not Path(path).exists():
        return 0
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]", text))

