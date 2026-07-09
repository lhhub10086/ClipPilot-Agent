from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clip_pilot.tools.transcript_assembly_tool import assemble_transcript


def run_timeline_repair_round(
    *,
    editor_timeline: dict[str, Any],
    judge_response: dict[str, Any],
    output_dir: str,
    round_index: int,
    policy_report: dict[str, Any] | None = None,
    task_plan: dict[str, Any] | None = None,
    semantic_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    repair_dir = Path(output_dir) / f"repair_round_{round_index}"
    repair_dir.mkdir(parents=True, exist_ok=True)
    repaired, actions = apply_repair(editor_timeline, judge_response, policy_report=policy_report, task_plan=task_plan, semantic_blocks=semantic_blocks)

    timeline_path = repair_dir / "editor_timeline.json"
    actions_path = repair_dir / "repair_actions_applied.json"
    timeline_path.write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")
    actions_path.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8")
    transcript_result = assemble_transcript(repaired, str(repair_dir / "final_review_transcript.md"), str(repair_dir / "final_review_transcript.txt"))

    return {
        "success": True,
        "backend": "judge_driven_timeline_repair",
        "output_path": str(timeline_path),
        "data": {
            "editor_timeline": repaired,
            "repair_actions": actions,
            "repair_actions_path": str(actions_path),
            "transcript_path": transcript_result["data"]["markdown_path"],
            "repair_round": round_index,
            "timeline_changed": timeline_fingerprint(editor_timeline) != timeline_fingerprint(repaired),
        },
    }


def apply_repair(
    timeline: dict[str, Any],
    judge_response: dict[str, Any],
    policy_report: dict[str, Any] | None = None,
    task_plan: dict[str, Any] | None = None,
    semantic_blocks: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    instruction = judge_response.get("repair_instruction", {}) if isinstance(judge_response.get("repair_instruction"), dict) else {}
    original_items = list(timeline.get("timeline_items", []))
    items = [dict(item) for item in original_items]
    actions: dict[str, Any] = {
        "received_major_problems": judge_response.get("major_problems", []),
        "received_segment_feedback": judge_response.get("segment_feedback", []),
        "received_repair_instruction": instruction,
        "dropped_segments": [],
        "inserted_bridges": [],
        "reordered_chronologically": False,
        "switched_to_single_topic": False,
        "prevented_empty_timeline": False,
        "received_policy_violations": (policy_report or {}).get("violations", []),
        "policy_reduce_scope": False,
    }

    drop = set(instruction.get("drop_segments") or [])
    if drop and len(drop) < len(items):
        before = len(items)
        items = [item for item in items if item.get("segment_id") not in drop]
        actions["dropped_segments"] = sorted(drop)
        actions["drop_count"] = before - len(items)
    elif drop and len(drop) >= len(items):
        actions["prevented_empty_timeline"] = True

    for bridge in instruction.get("insert_bridges") or []:
        if not isinstance(bridge, dict):
            continue
        target = bridge.get("after_segment_id") or bridge.get("segment_id")
        text = bridge.get("bridge_text") or bridge.get("bridge_after") or bridge.get("text")
        if not target or not text:
            continue
        for item in items:
            if item.get("segment_id") == target:
                item["bridge_after"] = text
                actions["inserted_bridges"].append({"segment_id": target, "bridge_after": text})

    for problem in judge_response.get("major_problems", []) or []:
        if not isinstance(problem, dict) or problem.get("repair_action") != "insert_bridge":
            continue
        target = _bridge_target_from_location(str(problem.get("location", "")), items)
        bridge_text = _bridge_text_for_problem(str(problem.get("problem", "")))
        if not target or not bridge_text:
            continue
        for item in items:
            if item.get("segment_id") == target and not item.get("bridge_before"):
                item["bridge_before"] = bridge_text
                actions["inserted_bridges"].append({"segment_id": target, "bridge_before": bridge_text, "source": "major_problem"})

    if instruction.get("switch_to_single_topic") and len(items) > 1:
        first_blocks = set(items[0].get("source_block_ids", []))
        related = [item for item in items if set(item.get("source_block_ids", [])) & first_blocks]
        if related:
            items = related
            actions["switched_to_single_topic"] = True

    starts_before = [float(item.get("source_start", 0.0)) for item in items]
    items = sorted(items, key=lambda item: float(item.get("source_start", 0.0)))
    actions["reordered_chronologically"] = starts_before != [float(item.get("source_start", 0.0)) for item in items]

    if not items and original_items:
        best = max(original_items, key=lambda item: float(item.get("duration", 0.0)))
        items = [dict(best)]
        actions["prevented_empty_timeline"] = True

    if policy_report and not policy_report.get("policy_valid", True):
        items, policy_actions = reduce_scope_for_policy(items, task_plan or {}, semantic_blocks or [])
        actions.update(policy_actions)

    repaired = {**timeline, "timeline_items": items, "repair_applied": True}
    actions["timeline_changed"] = timeline_fingerprint(timeline) != timeline_fingerprint(repaired)
    return repaired, actions


def reduce_scope_for_policy(items: list[dict[str, Any]], task_plan: dict[str, Any], semantic_blocks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    duration_policy = task_plan.get("duration_policy", {})
    count_policy = task_plan.get("segment_count_policy", {})
    max_final = float(duration_policy.get("max_final_duration_seconds") or 10**9)
    max_segment = float(duration_policy.get("max_segment_seconds") or 10**9)
    max_segments = int(count_policy.get("max_segments") or 10**9)
    target_segments = int(count_policy.get("target_segments") or min(max_segments, 8))
    max_selected_segments = max(1, min(max_segments, target_segments, 12))
    tolerance = 5.0
    block_map = {block.get("block_id"): block for block in semantic_blocks}
    candidates: list[dict[str, Any]] = []
    for item in items:
        origin_segment_id = item.get("origin_segment_id") or _origin_segment_id(str(item.get("segment_id", "")))
        block_ids = [block_id for block_id in item.get("source_block_ids", []) if block_id in block_map]
        if block_ids:
            for block_id in block_ids:
                block = block_map[block_id]
                duration = round(float(block.get("end", 0.0)) - float(block.get("start", 0.0)), 3)
                if duration <= max_segment + tolerance:
                    new_item = {
                        **item,
                        "segment_id": f"{item.get('segment_id')}_{block_id}",
                        "source_block_ids": [block_id],
                        "source_start": round(float(block.get("start", 0.0)), 3),
                        "source_end": round(float(block.get("end", 0.0)), 3),
                        "duration": duration,
                        "transcript": block.get("text", ""),
                        "why_included": f"Policy repair kept concise block {block_id}.",
                        "origin_segment_id": origin_segment_id,
                        "bridge_before": None,
                        "bridge_after": None,
                    }
                    candidates.append(new_item)
        elif float(item.get("duration", 0.0)) <= max_segment + tolerance:
            candidates.append({**item, "origin_segment_id": origin_segment_id, "bridge_before": None, "bridge_after": None})
    if not candidates:
        candidates = [item for item in items if float(item.get("duration", 0.0)) <= max_final + tolerance]
    candidates.sort(key=lambda item: float(item.get("source_start", 0.0)))
    candidates = _prefer_single_topic_cluster(candidates)
    selected = []
    total = 0.0
    for item in candidates:
        duration = float(item.get("duration", 0.0))
        if len(selected) >= max_selected_segments:
            break
        if total + duration > max_final + tolerance:
            continue
        selected.append(item)
        total += duration
    if not selected and candidates:
        selected = [min(candidates, key=lambda item: float(item.get("duration", 0.0)))]
    # Policy repair is a scope-reduction pass. Reusing bridges from a previous
    # long-form timeline can create false transitions after every micro block,
    # so keep the repaired timeline plain unless the editor explicitly adds a
    # new bridge in a later semantic repair pass.
    for item in selected:
        item["bridge_before"] = None
        item["bridge_after"] = None
    return selected, {
        "policy_reduce_scope": True,
        "policy_selected_count": len(selected),
        "policy_repaired_duration": round(sum(float(item.get("duration", 0.0)) for item in selected), 3),
        "policy_max_selected_segments": max_selected_segments,
        "policy_selected_origin": selected[0].get("origin_segment_id") if selected else None,
    }


def judge_passed(judge_response: dict[str, Any]) -> bool:
    return bool(judge_response.get("passed")) and float(judge_response.get("score", 0.0)) >= 0.75 and not judge_response.get("major_problems")


def timeline_fingerprint(timeline: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (
            item.get("segment_id"),
            tuple(item.get("source_block_ids", [])),
            round(float(item.get("source_start", 0.0)), 3),
            round(float(item.get("source_end", 0.0)), 3),
            item.get("bridge_before"),
            item.get("bridge_after"),
        )
        for item in timeline.get("timeline_items", [])
    ]


def _origin_segment_id(segment_id: str) -> str:
    parts = segment_id.split("_block_")
    return parts[0] if parts else segment_id


def _prefer_single_topic_cluster(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        groups.setdefault(str(item.get("origin_segment_id") or _origin_segment_id(str(item.get("segment_id", "")))), []).append(item)
    if not groups:
        return candidates
    # A policy repair should reduce scope, not fill the entire budget with
    # loosely related topics. Prefer the richest single source segment so the
    # repaired transcript stays coherent and Judge responses remain bounded.
    best_group = max(groups.values(), key=lambda group: (len(group), sum(float(item.get("duration", 0.0)) for item in group)))
    return sorted(best_group, key=lambda item: float(item.get("source_start", 0.0)))


def _bridge_target_from_location(location: str, items: list[dict[str, Any]]) -> str | None:
    ids = [str(item.get("segment_id", "")) for item in items]
    for segment_id in ids:
        if segment_id and segment_id in location:
            # If the problem is "between A and B", bridge before B.
            after = location.split(segment_id, 1)[-1]
            for later_id in ids:
                if later_id != segment_id and later_id in after:
                    return later_id
    return ids[1] if len(ids) > 1 else None


def _bridge_text_for_problem(problem: str) -> str:
    lower = problem.lower()
    if "multi-core" in lower or "multiple" in lower or "core" in lower:
        return "Next, the timeline moves from single-processor optimization to multi-core improvements."
    if "supercomputer" in lower or "processor configuration" in lower:
        return "When one machine is not enough, the explanation extends to multi-processor systems."
    if "topic" in lower or "transition" in lower or "abrupt" in lower:
        return "The next segment continues the performance-improvement thread."
    return "The next segment continues the same explanation thread."


# Backward-compatible helpers used by existing tests.
def run_repair_loop(**kwargs: Any) -> dict[str, Any]:
    result = run_timeline_repair_round(
        editor_timeline=kwargs["editor_timeline"],
        judge_response=kwargs["judge_response"],
        output_dir=kwargs["output_dir"],
        round_index=1,
        policy_report=kwargs.get("policy_report"),
        task_plan=kwargs.get("task_plan"),
        semantic_blocks=kwargs.get("semantic_blocks"),
    )
    return {
        "success": result["success"],
        "backend": result["backend"],
        "data": {"editor_timeline": result["data"]["editor_timeline"], "judge_response": kwargs["judge_response"], "repair_rounds": 1, "rounds": [result["data"]]},
    }

