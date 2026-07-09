from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_REQUIRED_GOALS = [
    "\u521d\u9ad8\u4e2d\u7269\u7406\u7684\u533a\u522b\u4e0e\u8054\u7cfb",
    "\u9ad8\u4e2d\u7269\u7406\u5b66\u4e60\u5185\u5bb9\u6216\u77e5\u8bc6\u7ed3\u6784",
    "\u5b66\u4e60\u65b9\u6cd5\u63d0\u9192",
]

DEFAULT_OPTIONAL_GOALS = ["\u5178\u578b\u4f8b\u9898", "\u6613\u9519\u70b9"]
DEFAULT_ROLES = ["introduction", "core_explanation", "method_or_example", "closing_or_summary"]


def extract_content_goals(intent: str) -> dict[str, list[str]]:
    text = intent or ""
    required = list(DEFAULT_REQUIRED_GOALS)
    optional = list(DEFAULT_OPTIONAL_GOALS)
    if "\u4f8b\u9898" in text and "\u5178\u578b\u4f8b\u9898" not in required:
        optional.append("\u4f8b\u9898\u8bb2\u89e3")
    if "\u6613\u9519" in text and "\u6613\u9519\u70b9" not in optional:
        optional.append("\u6613\u9519\u70b9")
    return {"required_content_goals": required, "optional_content_goals": sorted(set(optional)), "minimum_narrative_roles": DEFAULT_ROLES}


def validate_task_coverage(
    *,
    user_intent: str,
    task_plan: dict[str, Any] | None,
    editor_timeline: dict[str, Any],
    transcript_markdown_path: str,
    semantic_blocks: list[dict[str, Any]] | None = None,
    output_path: str,
) -> dict[str, Any]:
    report = build_task_coverage_report(
        user_intent=user_intent,
        task_plan=task_plan or {},
        editor_timeline=editor_timeline,
        transcript_markdown_path=transcript_markdown_path,
        semantic_blocks=semantic_blocks or [],
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "task_coverage_validator", "output_path": str(path), "data": report}


def build_task_coverage_report(
    *,
    user_intent: str,
    task_plan: dict[str, Any],
    editor_timeline: dict[str, Any],
    transcript_markdown_path: str = "",
    semantic_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    goals = task_plan.get("required_content_goals") or extract_content_goals(user_intent)["required_content_goals"]
    optional_goals = task_plan.get("optional_content_goals") or extract_content_goals(user_intent)["optional_content_goals"]
    min_roles = task_plan.get("minimum_narrative_roles") or extract_content_goals(user_intent)["minimum_narrative_roles"]
    items = editor_timeline.get("timeline_items", [])
    text = _timeline_text(items)
    if not text and transcript_markdown_path and Path(transcript_markdown_path).exists():
        text = Path(transcript_markdown_path).read_text(encoding="utf-8", errors="ignore")
    role_map = _role_coverage(items, text)
    required_reports = [_goal_report(goal, text, items, optional=False) for goal in goals]
    optional_reports = [_goal_report(goal, text, items, optional=True) for goal in optional_goals]
    covered_required = sum(1 for item in required_reports if item["covered"])
    role_score = sum(1 for role in min_roles if role_map.get(role, False)) / max(1, len(min_roles))
    goal_score = covered_required / max(1, len(required_reports))
    duration = sum(float(item.get("duration", 0.0) or 0.0) for item in items)
    segment_count = len(items)
    coverage_score = round(0.75 * goal_score + 0.25 * role_score, 3)
    degenerate_reasons = []
    if segment_count <= 1:
        degenerate_reasons.append("single_segment_only")
    if goal_score < 0.67:
        degenerate_reasons.append("insufficient_topic_coverage")
    if not role_map.get("core_explanation"):
        degenerate_reasons.append("no_core_explanation")
    if not role_map.get("closing_or_summary"):
        degenerate_reasons.append("no_closing")
    if duration < 45:
        degenerate_reasons.append("too_short_for_review_task")
    degenerate = bool(degenerate_reasons)
    task_coverage_valid = goal_score >= 0.67 and not {"insufficient_topic_coverage"} & set(degenerate_reasons)
    content_sufficiency_valid = not degenerate and coverage_score >= 0.7
    return {
        "task_coverage_valid": task_coverage_valid,
        "content_sufficiency_valid": content_sufficiency_valid,
        "coverage_score": coverage_score,
        "required_content_goals": required_reports,
        "optional_content_goals": optional_reports,
        "narrative_roles": {role: bool(role_map.get(role)) for role in min_roles},
        "timeline_duration": round(duration, 3),
        "segment_count": segment_count,
        "degenerate_output": degenerate,
        "degenerate_reasons": degenerate_reasons,
        "recommendation": "proceed" if task_coverage_valid and content_sufficiency_valid else "repair_or_targeted_manual_review_required",
    }


def repair_preserves_coverage(before: dict[str, Any], after: dict[str, Any], max_drop: float = 0.2) -> dict[str, Any]:
    before_score = float(before.get("coverage_score", 0.0) or 0.0)
    after_score = float(after.get("coverage_score", 0.0) or 0.0)
    accepted = after_score + max_drop >= before_score and not after.get("degenerate_output", False)
    return {
        "repair_accepted": accepted,
        "coverage_score_before": before_score,
        "coverage_score_after": after_score,
        "coverage_drop": round(before_score - after_score, 3),
        "degenerate_output_detected": bool(after.get("degenerate_output", False)),
    }


def _timeline_text(items: list[dict[str, Any]]) -> str:
    return "\n".join(str(item.get("transcript") or item.get("text") or "") for item in items)


def _goal_report(goal: str, text: str, items: list[dict[str, Any]], optional: bool) -> dict[str, Any]:
    keywords = _keywords_for_goal(goal)
    evidence = []
    for item in items:
        item_text = str(item.get("transcript") or item.get("text") or "")
        if any(keyword in item_text for keyword in keywords):
            evidence.append(item.get("segment_id", item.get("item_id", "")))
    return {"goal": goal, "covered": bool(evidence), "evidence_segment_ids": [eid for eid in evidence if eid], "optional": optional}


def _keywords_for_goal(goal: str) -> list[str]:
    mapping = {
        "\u521d\u9ad8\u4e2d\u7269\u7406\u7684\u533a\u522b\u4e0e\u8054\u7cfb": ["\u521d\u4e2d\u7269\u7406", "\u9ad8\u4e2d\u7269\u7406", "\u533a\u522b", "\u8054\u7cfb"],
        "\u9ad8\u4e2d\u7269\u7406\u5b66\u4e60\u5185\u5bb9\u6216\u77e5\u8bc6\u7ed3\u6784": ["\u9ad8\u4e2d\u7269\u7406\u8981\u5b66", "\u8fd0\u52a8\u5b66", "\u529b\u5b66", "\u5b66\u4e60\u987a\u5e8f", "\u6559\u6750", "\u5b66\u4ec0\u4e48"],
        "\u5b66\u4e60\u65b9\u6cd5\u63d0\u9192": ["\u5b66\u4e60\u65b9\u6cd5", "\u5b66\u597d", "\u6ce8\u610f", "\u65b9\u6cd5", "\u590d\u4e60", "\u7ec3\u4e60", "\u6293\u597d"],
        "\u5178\u578b\u4f8b\u9898": ["\u4f8b\u9898", "\u9898", "\u516c\u5f0f", "\u89e3\u9898"],
        "\u6613\u9519\u70b9": ["\u6613\u9519", "\u9519\u8bef", "\u6ce8\u610f", "\u96be\u70b9"],
    }
    return mapping.get(goal, [goal])


def _role_coverage(items: list[dict[str, Any]], text: str) -> dict[str, bool]:
    roles = {str(item.get("role", "")) for item in items}
    return {
        "introduction": bool(roles & {"hook", "introduction"} or re.search(r"\u7b2c\u4e00\u4e2a|\u4eca\u5929|\u95ee\u9898|\u533a\u522b|\u8054\u7cfb", text)),
        "core_explanation": bool(roles & {"core_concept", "explanation"} and len(text) > 120),
        "method_or_example": bool(re.search(r"\u65b9\u6cd5|\u4f8b\u9898|\u516c\u5f0f|\u600e\u4e48|\u5982\u4f55|\u6ce8\u610f|\u5b66\u597d", text)),
        "closing_or_summary": bool(roles & {"summary", "closing"} or re.search(r"\u6700\u540e|\u603b\u7ed3|\u6240\u4ee5|\u5173\u952e|\u8bb0\u4f4f", text)),
    }

