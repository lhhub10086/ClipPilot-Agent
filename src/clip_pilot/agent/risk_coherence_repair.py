from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clip_pilot.agent.timeline_editor import normalize_editor_timeline
from clip_pilot.tools.task_coverage_validator import repair_preserves_coverage
from clip_pilot.tools.selection_scope_transcript_gate import write_manual_review_queue
from clip_pilot.tools.transcript_assembly_tool import assemble_transcript


def run_risk_coherence_repair(
    *,
    editor_timeline: dict[str, Any],
    coherence_gap_report: dict[str, Any],
    semantic_blocks: list[dict[str, Any]],
    output_dir: str,
    sentence_units_path: str | None = None,
    asr_risk_report_path: str | None = None,
    transcript_resolution_path: str | None = None,
    video_path: str | None = None,
) -> dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    block_map = {str(block.get("block_id")): block for block in semantic_blocks}
    repaired, actions = repair_timeline(editor_timeline, coherence_gap_report, semantic_blocks)
    timeline_path = root / "risk_coherence_repaired_timeline.json"
    actions_path = root / "risk_coherence_repair_actions.json"
    timeline_path.write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")
    actions_path.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8")
    transcript = assemble_transcript(repaired, str(root / "risk_coherence_repaired_transcript.md"), str(root / "risk_coherence_repaired_transcript.txt"))
    manual_ids = coherence_gap_report.get("required_manual_review_sentence_ids", [])
    review_path = ""
    if manual_ids and sentence_units_path and asr_risk_report_path:
        review_path = str(root / "subtitle_manual_review_current_edit.csv")
        write_manual_review_queue(
            sentence_units_path=sentence_units_path,
            asr_risk_report_path=asr_risk_report_path,
            transcript_resolution_path=transcript_resolution_path,
            output_csv_path=review_path,
            video_path=video_path,
            assets_dir=str(root / "manual_review_assets"),
            required_sentence_ids=manual_ids,
            generate_audio_assets=True,
        )
    return {
        "success": True,
        "backend": "risk_coherence_joint_repair",
        "output_path": str(timeline_path),
        "data": {
            "editor_timeline": repaired,
            "actions": actions,
            "actions_path": str(actions_path),
            "transcript_path": transcript["data"]["markdown_path"],
            "manual_review_csv": review_path,
            "timeline_changed": editor_timeline != repaired,
        },
    }


def repair_timeline(editor_timeline: dict[str, Any], coherence_gap_report: dict[str, Any], semantic_blocks: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    block_map = {str(block.get("block_id")): block for block in semantic_blocks}
    items = [dict(item) for item in editor_timeline.get("timeline_items", [])]
    actions: dict[str, Any] = {
        "safe_replacements": [],
        "expanded_context": [],
        "reduced_scope": False,
        "targeted_manual_review_sentence_ids": coherence_gap_report.get("required_manual_review_sentence_ids", []),
        "switch_to_single_topic_reason": None,
    }
    for gap in coherence_gap_report.get("gaps", []):
        if gap.get("recommended_action") == "safe_replacement" and gap.get("safe_alternative_candidates"):
            replacement = gap["safe_alternative_candidates"][0]
            target = _target_segment(gap, items)
            if target and replacement.get("block_id") in block_map:
                target["source_block_ids"] = [replacement["block_id"]]
                actions["safe_replacements"].append({"segment_id": target.get("segment_id"), "block_id": replacement["block_id"]})
        elif gap.get("recommended_action") == "expand_context" and gap.get("safe_alternative_candidates"):
            replacement = gap["safe_alternative_candidates"][0]
            target = _target_segment(gap, items)
            if target and replacement.get("block_id") in block_map and replacement["block_id"] not in target.get("source_block_ids", []):
                target["source_block_ids"] = sorted(set(target.get("source_block_ids", []) + [replacement["block_id"]]), key=lambda bid: float(block_map[bid].get("start", 0.0)))
                actions["expanded_context"].append({"segment_id": target.get("segment_id"), "block_id": replacement["block_id"]})

    if _still_fragmented(items, block_map) or not actions["safe_replacements"] and not actions["expanded_context"]:
        items = _single_topic_fallback(items, block_map)
        actions["reduced_scope"] = True
        actions["switch_to_single_topic_reason"] = "Timeline remained fragmented after risk-aware repair; kept the richest low-risk contiguous topic cluster."

    payload = normalize_editor_timeline(
        {
            "timeline_items": [
                {
                    "segment_id": item.get("segment_id"),
                    "role": item.get("role", "core_concept"),
                    "source_block_ids": item.get("source_block_ids", []),
                    "why_included": item.get("why_included", "Risk-coherence repaired item."),
                    "bridge_before": item.get("bridge_before"),
                    "bridge_after": item.get("bridge_after"),
                    "expected_viewer_understanding": item.get("expected_viewer_understanding", ""),
                }
                for item in items
            ],
            "editing_strategy": {
                "mode": "single_topic" if actions["reduced_scope"] else editor_timeline.get("editing_strategy", {}).get("mode", "highlight_reel"),
                "reason": actions["switch_to_single_topic_reason"] or "Risk-coherence repair kept safe coherent alternatives.",
                "quality_over_count": True,
                "allow_variable_segment_duration": True,
                "coherence_strategy": "single_topic_first",
            },
        },
        block_map,
    )
    payload["risk_coherence_repair_applied"] = True
    return payload, actions


def assess_repair_tradeoff(before_coverage: dict[str, Any], after_coverage: dict[str, Any], before_timeline: dict[str, Any], after_timeline: dict[str, Any]) -> dict[str, Any]:
    decision = repair_preserves_coverage(before_coverage, after_coverage)
    before_items = before_timeline.get("timeline_items", [])
    after_items = after_timeline.get("timeline_items", [])
    before_duration = sum(float(item.get("duration", 0.0) or 0.0) for item in before_items)
    after_duration = sum(float(item.get("duration", 0.0) or 0.0) for item in after_items)
    decision.update(
        {
            "segment_count_before": len(before_items),
            "segment_count_after": len(after_items),
            "duration_before": round(before_duration, 3),
            "duration_after": round(after_duration, 3),
        }
    )
    if len(before_items) > 1 and len(after_items) <= 1 and after_duration < 45:
        decision["repair_accepted"] = False
        decision["degenerate_output_detected"] = True
        decision["rejection_reason"] = "repair_collapsed_to_single_short_segment"
    return decision


def _target_segment(gap: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any] | None:
    between = set(gap.get("between", []))
    for item in items:
        if item.get("segment_id") in between:
            return item
    return items[0] if items else None


def _still_fragmented(items: list[dict[str, Any]], block_map: dict[str, dict[str, Any]]) -> bool:
    starts = []
    for item in items:
        block_ids = [bid for bid in item.get("source_block_ids", []) if bid in block_map]
        if not block_ids:
            continue
        starts.append(min(float(block_map[bid].get("start", 0.0)) for bid in block_ids))
    if len(starts) < 2:
        return False
    starts = sorted(starts)
    return any((b - a) > 420 for a, b in zip(starts, starts[1:]))


def _single_topic_fallback(items: list[dict[str, Any]], block_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        score = 0.0
        block_ids = [bid for bid in item.get("source_block_ids", []) if bid in block_map and block_map[bid].get("lexical_risk_level") == "low_risk"]
        if not block_ids:
            continue
        starts = [float(block_map[bid].get("start", 0.0)) for bid in block_ids]
        ends = [float(block_map[bid].get("end", 0.0)) for bid in block_ids]
        span = max(starts) - min(starts) if len(starts) > 1 else 0
        total_duration = max(ends) - min(starts) if ends else 0
        score += min(len(block_ids), 5) * 0.35
        score += sum(float(block_map[bid].get("narrative_importance", 0.0) or 0.0) for bid in block_ids)
        score -= span / 250
        score -= min(starts) / 120
        score -= max(0.0, (total_duration - 180) / 100)
        candidates.append((score, {**item, "source_block_ids": block_ids[:4]}))
    if candidates:
        best = max(candidates, key=lambda pair: pair[0])[1]
        best["segment_id"] = "segment_001"
        best["role"] = "core_concept"
        best["bridge_before"] = None
        best["bridge_after"] = None
        return [best]
    return items[:1]

