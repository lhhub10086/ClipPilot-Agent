from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def analyze_coherence_gaps(
    *,
    judge_response: dict[str, Any],
    editor_timeline: dict[str, Any],
    semantic_blocks: list[dict[str, Any]],
    selector_response: dict[str, Any] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    block_map = {str(block.get("block_id")): block for block in semantic_blocks}
    selected_block_ids = {
        str(block_id)
        for item in editor_timeline.get("timeline_items", [])
        for block_id in item.get("source_block_ids", [])
    }
    excluded_risky = [
        block
        for block in semantic_blocks
        if block.get("contains_unresolved_asr") and str(block.get("block_id")) not in selected_block_ids
    ]
    gaps = []
    for problem in judge_response.get("major_problems", []) or []:
        if not isinstance(problem, dict):
            continue
        gap = _gap_from_problem(problem, editor_timeline, excluded_risky, block_map)
        gaps.append(gap)
    if not gaps and not judge_response.get("passed", False):
        gaps.append(_fallback_gap(editor_timeline, excluded_risky))
    manual_ids = sorted({sid for gap in gaps for candidate in gap.get("excluded_candidates_near_gap", []) if candidate.get("required_for_coherence") for sid in candidate.get("unresolved_sentence_ids", [])})
    payload = {
        "judge_score": judge_response.get("score"),
        "gap_count": len(gaps),
        "gaps": gaps,
        "manual_review_can_recover_coherence": bool(manual_ids),
        "required_manual_review_sentence_ids": manual_ids,
        "coherence_status": "failed_due_to_exclusions" if manual_ids else ("failed_needs_single_topic_or_safe_repair" if gaps else "passed"),
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _gap_from_problem(problem: dict[str, Any], timeline: dict[str, Any], excluded_risky: list[dict[str, Any]], block_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    location = str(problem.get("location", ""))
    segment_ids = _segment_ids_from_location(location, timeline)
    span = _span_for_segments(segment_ids, timeline)
    near = _nearby_candidates(span, excluded_risky)
    safe_replacements = _safe_replacements(span, block_map, timeline)
    if safe_replacements:
        action = "safe_replacement"
    elif any(item.get("lexical_risk_level") == "medium_risk" for item in near):
        action = "manual_review_bridge"
    elif problem.get("repair_action") == "expand_context":
        action = "expand_context"
    else:
        action = "reduce_scope"
    return {
        "between": segment_ids,
        "problem": problem.get("problem", ""),
        "missing_topic_or_context": _missing_context(problem),
        "excluded_candidates_near_gap": [_candidate_summary(item, span) for item in near[:8]],
        "safe_alternative_candidates": [_candidate_summary(item, span) for item in safe_replacements[:8]],
        "recommended_action": action,
    }


def _fallback_gap(timeline: dict[str, Any], excluded_risky: list[dict[str, Any]]) -> dict[str, Any]:
    items = timeline.get("timeline_items", [])
    segment_ids = [item.get("segment_id") for item in items[:2]]
    span = (float(items[0].get("source_start", 0.0)), float(items[-1].get("source_end", 0.0))) if items else (0.0, 0.0)
    near = _nearby_candidates(span, excluded_risky)
    return {
        "between": segment_ids,
        "problem": "Judge failed without a precise gap location.",
        "missing_topic_or_context": "Need a narrower or better bridged storyline.",
        "excluded_candidates_near_gap": [_candidate_summary(item, span) for item in near[:8]],
        "safe_alternative_candidates": [],
        "recommended_action": "reduce_scope",
    }


def _segment_ids_from_location(location: str, timeline: dict[str, Any]) -> list[str]:
    ids = [str(item.get("segment_id")) for item in timeline.get("timeline_items", [])]
    found = [segment_id for segment_id in ids if segment_id and segment_id in location]
    if found:
        return found
    match = re.findall(r"segment_\d+", location)
    return match or ids[:2]


def _span_for_segments(segment_ids: list[str], timeline: dict[str, Any]) -> tuple[float, float]:
    items = [item for item in timeline.get("timeline_items", []) if item.get("segment_id") in segment_ids]
    if not items:
        all_items = timeline.get("timeline_items", [])
        items = all_items[:2]
    if not items:
        return (0.0, 0.0)
    return (min(float(item.get("source_start", 0.0)) for item in items), max(float(item.get("source_end", 0.0)) for item in items))


def _nearby_candidates(span: tuple[float, float], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start, end = span
    ranked = []
    for block in blocks:
        b_start = float(block.get("start", 0.0))
        b_end = float(block.get("end", 0.0))
        distance = min(abs(b_end - start), abs(b_start - end), abs(b_start - start))
        if distance <= 180 or (start <= b_start <= end):
            item = dict(block)
            item["_distance"] = distance
            item["required_for_coherence"] = block.get("lexical_risk_level") == "medium_risk" or float(block.get("bridge_importance", 0.0) or 0.0) >= 0.3
            ranked.append(item)
    ranked.sort(key=lambda item: (float(item.get("_distance", 0.0)), -float(item.get("bridge_importance", 0.0) or 0.0)))
    return ranked


def _safe_replacements(span: tuple[float, float], block_map: dict[str, dict[str, Any]], timeline: dict[str, Any]) -> list[dict[str, Any]]:
    selected = {
        str(block_id)
        for item in timeline.get("timeline_items", [])
        for block_id in item.get("source_block_ids", [])
    }
    start, end = span
    candidates = []
    for block in block_map.values():
        if str(block.get("block_id")) in selected or block.get("lexical_risk_level") != "low_risk":
            continue
        b_start = float(block.get("start", 0.0))
        distance = min(abs(b_start - start), abs(b_start - end))
        if distance <= 240:
            item = dict(block)
            item["_distance"] = distance
            candidates.append(item)
    candidates.sort(key=lambda item: (float(item.get("_distance", 0.0)), -float(item.get("narrative_importance", 0.0) or 0.0)))
    return candidates


def _candidate_summary(block: dict[str, Any], span: tuple[float, float]) -> dict[str, Any]:
    return {
        "block_id": block.get("block_id"),
        "editing_unit_id": block.get("editing_unit_id"),
        "start": block.get("start"),
        "end": block.get("end"),
        "risk_level": block.get("lexical_risk_level", "low_risk"),
        "lexical_risk_score": block.get("lexical_risk_score", 0.0),
        "narrative_importance": block.get("narrative_importance", 0.0),
        "bridge_importance": block.get("bridge_importance", 0.0),
        "required_for_coherence": bool(block.get("required_for_coherence", False)),
        "unresolved_sentence_ids": block.get("unresolved_sentence_ids", []),
        "summary": str(block.get("summary") or block.get("text") or "")[:120],
    }


def _missing_context(problem: dict[str, Any]) -> str:
    text = str(problem.get("problem", ""))
    if "gap" in text.lower() or "missing" in text.lower():
        return text[:200]
    return problem.get("type", "coherence gap")

