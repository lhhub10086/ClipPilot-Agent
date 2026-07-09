from __future__ import annotations

import time
from typing import Any

from .trace_recorder import TraceRecorder


class StepExecutor:
    def __init__(self, trace: TraceRecorder):
        self.trace = trace

    def run(self, *, step_name: str, tool_name: str, input_summary: dict[str, Any], func) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            result = func()
            success = bool(result.get("success", True))
            error = result.get("error")
        except Exception as exc:
            result = {}
            success = False
            error = str(exc)
        duration = round(time.perf_counter() - started, 3)
        event = {
            "step_name": step_name,
            "tool_name": tool_name,
            "success": success,
            "artifact_type": artifact_type_for(step_name),
            "input_summary": input_summary,
            "output_summary": summarize_result(result),
            "output_path": str(result.get("output_path", "")),
            "error": error,
            "duration_seconds": duration,
        }
        self.trace.record(event)
        if not success:
            raise RuntimeError(error or f"{step_name} failed")
        return result


def summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    summary = {key: result.get(key) for key in ["success", "backend", "error", "output_path"] if key in result}
    data = result.get("data")
    if isinstance(data, dict):
        for key in [
            "segment_count",
            "candidate_count",
            "selected_count",
            "subtitle_count",
            "duration",
            "has_audio",
            "row_count",
            "model",
            "prompt_hash",
            "raw_response_path",
            "task_plan_path",
            "fallback_used",
            "fallback_reason",
            "parsed_response_path",
            "repair_round",
            "score",
            "repair_actions_path",
            "transcript_path",
            "timeline_changed",
            "policy_valid",
            "final_duration_seconds",
            "max_final_duration_seconds",
        ]:
            if key in data:
                summary[key] = data[key]
        if "task_plan" in data:
            task_plan = data["task_plan"]
            summary["parsed_task_plan"] = {
                "task_type": task_plan.get("task_type"),
                "segment_count_policy": task_plan.get("segment_count_policy", {}),
                "duration_policy": task_plan.get("duration_policy", {}),
                "planner_backend": task_plan.get("planner_backend"),
                "planner_fallback_used": task_plan.get("planner_fallback_used"),
            }
        if "selector_response" in data:
            summary["selected_topics"] = len(data["selector_response"].get("selected_topics", []))
        if "editor_timeline" in data:
            summary["timeline_items"] = len(data["editor_timeline"].get("timeline_items", []))
        if "judge_response" in data:
            summary["score"] = data["judge_response"].get("score")
            summary["passed"] = data["judge_response"].get("passed")
            summary["major_problem_count"] = len(data["judge_response"].get("major_problems", []))
        if "export_gate_decision" in data:
            summary["video_export_allowed"] = data["export_gate_decision"].get("video_export_allowed")
    return summary


def artifact_type_for(step_name: str) -> str:
    if step_name.startswith("judge_llm_call_round_"):
        return "judge_response_json"
    if step_name.startswith("timeline_repair_round_"):
        return "repair_round_artifacts"
    if step_name.startswith("policy_validation_round_"):
        return "policy_validation_json"
    mapping = {
        "intent_parse": "workflow_metadata",
        "planner_llm_call": "task_plan_policy",
        "task_planning": "task_plan_policy",
        "subtitle_parse": "subtitle_input",
        "sentence_segmentation": "sentence_segments",
        "semantic_block_generation": "semantic_blocks",
        "storyline_planner_llm_call": "storyline_plan_json",
        "selector_llm_call": "selector_response_json",
        "editor_llm_call": "editor_timeline_json",
        "final_review_transcript_generation": "final_review_transcript",
        "judge_llm_call": "judge_response_json",
        "timeline_repair_loop": "repair_loop",
        "export_gate_decision": "export_gate_json",
        "semantic_clip_selection": "semantic_selected_segments",
        "semantic_timeline_generation": "semantic_timeline_json",
        "coherence_validation": "semantic_coherence_report",
        "transcript_review_generation": "transcript_review_markdown",
        "candidate_generation": "candidate_segments",
        "clip_selection": "selected_segment_plan",
        "llm_content_generation": "llm_generated_metadata",
        "selected_segment_export": "intermediate_video_assets",
        "title_card_generation": "optional_title_card_assets",
        "timeline_generation": "timeline_json",
        "final_subtitle_generation": "final_review_srt",
        "final_review_video_generation": "primary_video_output",
        "edit_plan_generation": "edit_plan_json",
        "review_sheet_generation": "human_review_csv",
        "artifact_validation": "validation_report_json",
    }
    return mapping.get(step_name, "unknown")

