from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clip_pilot.schemas.trace_schema import validate_trace
from clip_pilot.tools.media_probe_tool import probe_media


class ArtifactValidator:
    def validate(self, out_dir: str, final_video_result: dict[str, Any] | None = None) -> dict[str, Any]:
        root = Path(out_dir)
        trace = _read_json(root / "trace.json")
        quality = _read_json(root / "transcript_quality_report.json")
        gate = _read_json(root / "export_gate_decision.json")
        judge = _read_json(root / "judge_response_round_1.json")
        policy = _read_json(root / "policy_validation_report.json")
        final_exists = _non_empty(root / "final_review.mp4")
        final_probe = probe_media(str(root / "final_review.mp4")) if final_exists else {}

        transcript_valid = bool((quality or {}).get("transcript_valid", False))
        content_valid = bool((gate or {}).get("content_valid", (gate or {}).get("video_export_allowed", False)))
        policy_valid = bool((gate or {}).get("policy_valid", (policy or {}).get("policy_valid", False)))
        video_export_allowed = bool((gate or {}).get("video_export_allowed", False))
        video_exported = final_exists
        media_valid = (not video_exported) or bool(final_probe.get("visual_valid"))

        checks = [
            _check("trace_exists", _non_empty(root / "trace.json")),
            _check("workflow_summary_exists", _non_empty(root / "workflow_summary.json")),
            _check("transcript_quality_report_exists", _non_empty(root / "transcript_quality_report.json")),
            _check("transcript_quality_step_recorded", _has_step(trace, "transcript_quality_check")),
            _check("transcript_valid", transcript_valid),
        ]

        blocked_reason = None
        if not transcript_valid:
            blocked_reason = "transcript_quality_failed"
            checks.extend(
                [
                    _check("selector_not_run_when_transcript_invalid", not _non_empty(root / "selector_response.json")),
                    _check("editor_not_run_when_transcript_invalid", not _non_empty(root / "editor_timeline.json")),
                    _check("judge_not_run_when_transcript_invalid", not _non_empty(root / "judge_response_round_1.json")),
                    _check("no_video_export_when_transcript_invalid", not video_exported),
                ]
            )
            harness_behavior_valid = all(item["passed"] for item in checks if item["name"] != "transcript_valid")
        else:
            blocked_reason = None if video_export_allowed else ((gate or {}).get("blocked_reason") or "content_coherence_failed")
            initial_failed = _initial_judge_failed(judge)
            repair_rounds = int((gate or {}).get("repair_rounds", 0) or 0)
            checks.extend(
                [
                    _check("selector_response_exists", _non_empty(root / "selector_response.json")),
                    _check("editor_timeline_exists", _non_empty(root / "editor_timeline.json")),
                    _check("final_review_transcript_exists", _non_empty(root / "final_review_transcript.md")),
                    _check("judge_response_exists", _non_empty(root / "judge_response_round_1.json")),
                    _check("policy_validation_report_exists", _non_empty(root / "policy_validation_report.json")),
                    _check("final_duration_within_policy", _policy_check(policy, "final_duration_exceeds_policy")),
                    _check("segment_durations_within_policy", _policy_check(policy, "segment_duration_exceeds_policy")),
                    _check("segment_count_within_policy", _policy_check(policy, "segment_count_exceeds_policy") and _policy_check(policy, "segment_count_below_policy")),
                    _check("policy_valid_before_export", (not video_export_allowed) or policy_valid),
                    _check("export_blocked_when_policy_invalid", policy_valid or not video_export_allowed),
                    _check("policy_repair_triggered_when_duration_exceeded", _policy_repair_triggered_when_duration_exceeded(trace, policy, gate)),
                    _check("export_gate_decision_exists", _non_empty(root / "export_gate_decision.json")),
                    _check("judge_score_above_threshold_if_allowed", (not video_export_allowed) or float((gate or {}).get("judge_final_score", 0.0)) >= 0.75),
                    _check("no_video_export_when_gate_false", video_export_allowed or not video_exported),
                    _check("final_video_exists_when_gate_true_and_requested", _final_video_exists_when_requested(root, gate)),
                    _check("repair_loop_recorded_if_used", _repair_loop_recorded_if_used(root, trace, gate)),
                    _check("repair_loop_triggered_when_judge_failed", (not initial_failed) or repair_rounds > 0),
                    _check("repair_round_outputs_exist", _repair_round_outputs_exist(root, repair_rounds)),
                    _check("editor_timeline_changed_after_repair", (not initial_failed) or _editor_timeline_changed_after_repair(root, trace)),
                    _check("judge_recalled_after_repair", (not initial_failed) or _has_step(trace, "judge_llm_call_round_2")),
                    _check("no_direct_block_on_first_judge_failure_when_transcript_valid", (not initial_failed) or repair_rounds > 0),
                    _check("export_blocked_only_after_max_repair_if_transcript_valid", video_export_allowed or (not initial_failed) or repair_rounds >= 3),
                ]
            )
            if video_exported:
                checks.extend(
                    [
                        _check("final_review_probe_valid", bool(final_probe.get("exists")) and int(final_probe.get("frame_count") or 0) > 0),
                        _check("final_review_visual_valid", bool(final_probe.get("visual_valid"))),
                        _check("final_review_black_ratio_below_threshold", float(final_probe.get("black_frame_ratio", 1.0)) < 0.5),
                    ]
                )
            harness_behavior_valid = all(
                item["passed"]
                for item in checks
                if item["name"] not in {"transcript_valid", "final_duration_within_policy", "segment_durations_within_policy", "segment_count_within_policy"}
            )

        report = {
            "run_completed": True,
            "input_valid": _non_empty(Path(root) / "trace.json"),
            "transcript_valid": transcript_valid,
            "content_valid": content_valid,
            "policy_valid": policy_valid,
            "media_valid": media_valid,
            "video_export_allowed": video_export_allowed,
            "video_exported": video_exported,
            "harness_behavior_valid": harness_behavior_valid,
            "blocked_reason": blocked_reason,
            "checks": checks,
            "trace_errors": validate_trace(trace) if trace else ["missing trace"],
            "media_probes": {"final_review": final_probe},
        }
        return report


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _non_empty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _check(name: str, passed: bool, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _has_step(trace: dict[str, Any] | None, step_name: str) -> bool:
    if not trace:
        return False
    return any(step.get("step_name") == step_name for step in trace.get("steps", []))


def _final_video_exists_when_requested(root: Path, gate: dict[str, Any] | None) -> bool:
    if not gate:
        return False
    if not gate.get("export_requested"):
        return True
    return (not gate.get("video_export_allowed")) or _non_empty(root / "final_review.mp4")


def _repair_loop_recorded_if_used(root: Path, trace: dict[str, Any] | None, gate: dict[str, Any] | None) -> bool:
    rounds = int((gate or {}).get("repair_rounds", 0) or 0)
    if rounds <= 0:
        return True
    if not _has_step(trace, "timeline_repair_loop") and not _has_step(trace, "timeline_repair_round_1"):
        return False
    for idx in range(1, rounds + 1):
        repair_dir = root / f"repair_round_{idx}"
        if any(repair_dir.glob("judge_response_round_*.json")) or (repair_dir / "judge_response.json").exists():
            return True
    return False


def _initial_judge_failed(judge: dict[str, Any] | None) -> bool:
    if not judge:
        return False
    return (not judge.get("passed")) or float(judge.get("score", 0.0)) < 0.75 or bool(judge.get("major_problems"))


def _repair_round_outputs_exist(root: Path, rounds: int) -> bool:
    for idx in range(1, rounds + 1):
        repair_dir = root / f"repair_round_{idx}"
        required = [
            repair_dir / "editor_timeline.json",
            repair_dir / "final_review_transcript.md",
            repair_dir / "repair_actions_applied.json",
            repair_dir / "judge_response.json",
        ]
        if not all(_non_empty(path) for path in required):
            return False
    return True


def _editor_timeline_changed_after_repair(root: Path, trace: dict[str, Any] | None) -> bool:
    if not trace:
        return False
    for step in trace.get("steps", []):
        if str(step.get("step_name", "")).startswith("timeline_repair_round_"):
            if bool(step.get("output_summary", {}).get("timeline_changed")):
                return True
    actions = _read_json(root / "repair_round_1" / "repair_actions_applied.json") or {}
    return bool(actions.get("timeline_changed") or actions.get("reordered_chronologically") or actions.get("inserted_bridges") or actions.get("dropped_segments"))


def _policy_check(policy: dict[str, Any] | None, violation_type: str) -> bool:
    if not policy:
        return False
    return not any(item.get("type") == violation_type and item.get("severity") == "blocking" for item in policy.get("violations", []))


def _policy_repair_triggered_when_duration_exceeded(trace: dict[str, Any] | None, policy: dict[str, Any] | None, gate: dict[str, Any] | None) -> bool:
    if not policy:
        return False
    duration_exceeded = any(item.get("type") == "final_duration_exceeds_policy" for item in policy.get("violations", []))
    if not duration_exceeded:
        return True
    if gate and int(gate.get("repair_rounds", 0) or 0) > 0:
        return True
    return _has_step(trace, "timeline_repair_round_1")


def _segment_count_matches_policy(timeline: dict[str, Any], policy: dict[str, Any]) -> bool:
    count = len(timeline.get("items", []))
    count_policy = policy.get("segment_count_policy", {})
    min_segments = int(count_policy.get("min_segments") or 1)
    max_segments = int(count_policy.get("max_segments") or 999)
    allow_less = bool(count_policy.get("allow_less_than_target", True))
    if count == 0:
        return bool(policy.get("allow_no_valid_segments", False))
    if count > max_segments:
        return False
    return allow_less or count >= min_segments

