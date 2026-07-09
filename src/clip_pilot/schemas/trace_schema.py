from __future__ import annotations

from typing import Any


REQUIRED_TRACE_STEPS = [
    "input_validation",
    "intent_parse",
    "subtitle_parse",
    "transcript_quality_check",
    "planner_llm_call",
    "sentence_segmentation",
    "semantic_block_generation",
    "selector_llm_call",
    "editor_llm_call",
    "final_review_transcript_generation",
    "judge_llm_call",
    "timeline_repair_loop",
    "semantic_timeline_generation",
    "transcript_review_generation",
    "export_gate_decision",
    "artifact_validation",
]


def validate_trace(payload: dict[str, Any]) -> list[str]:
    steps = payload.get("steps", [])
    errors = []
    if not steps:
        return ["trace steps must be non-empty"]
    for idx, step in enumerate(steps, start=1):
        for key in ["step_name", "tool_name", "success", "input_summary", "output_summary", "output_path", "error", "duration_seconds"]:
            if key not in step:
                errors.append(f"step {idx} missing {key}")
    return errors

