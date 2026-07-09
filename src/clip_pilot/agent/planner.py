from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from clip_pilot.schemas.task_schema import normalize_task_plan
from clip_pilot.tools.task_coverage_validator import extract_content_goals
from clip_pilot.tools.llm_client import call_chat_completion


def build_workflow_plan() -> list[dict[str, str]]:
    return [
        {"step_name": "intent_parse", "tool_name": "intent_parser"},
        {"step_name": "planner_llm_call", "tool_name": "llm_planner"},
        {"step_name": "subtitle_parse", "tool_name": "subtitle_tool"},
        {"step_name": "sentence_segmentation", "tool_name": "sentence_segment_tool"},
        {"step_name": "semantic_block_generation", "tool_name": "semantic_block_tool"},
        {"step_name": "storyline_planner_llm_call", "tool_name": "storyline_planner"},
        {"step_name": "semantic_clip_selection", "tool_name": "semantic_block_tool"},
        {"step_name": "semantic_timeline_generation", "tool_name": "coherence_validator"},
        {"step_name": "coherence_validation", "tool_name": "coherence_validator"},
        {"step_name": "transcript_review_generation", "tool_name": "coherence_validator"},
        {"step_name": "llm_content_generation", "tool_name": "llm_tool"},
        {"step_name": "selected_segment_export", "tool_name": "segment_export_tool"},
        {"step_name": "title_card_generation", "tool_name": "title_card_tool"},
        {"step_name": "timeline_generation", "tool_name": "timeline_schema"},
        {"step_name": "final_subtitle_generation", "tool_name": "final_subtitle_tool"},
        {"step_name": "final_review_video_generation", "tool_name": "final_video_tool"},
        {"step_name": "edit_plan_generation", "tool_name": "edit_plan_schema"},
        {"step_name": "review_sheet_generation", "tool_name": "review_sheet_tool"},
        {"step_name": "artifact_validation", "tool_name": "artifact_validator"},
    ]


def build_task_plan(
    *,
    intent: str,
    video_metadata: dict[str, Any],
    subtitle_metadata: dict[str, Any],
    config: dict[str, Any],
    user_constraints: dict[str, Any] | None = None,
    output_dir: str | None = None,
    no_llm_planner: bool = False,
) -> dict[str, Any]:
    detected_task_type = detect_task_type(intent)
    defaults = load_policy_defaults(detected_task_type)
    constraints = user_constraints or {}
    explicit_count = constraints.get("target_segments") or extract_requested_count(intent)
    messages = build_planner_messages(intent, video_metadata, subtitle_metadata, defaults, constraints)
    prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    output_root = Path(output_dir) if output_dir else None
    raw_response_path = output_root / "planner_raw_response.json" if output_root else None
    task_plan_path = output_root / "task_plan.json" if output_root else None

    if no_llm_planner:
        llm = {
            "success": False,
            "backend": "llm_api",
            "model": config.get("llm", {}).get("model", "deepseek-chat"),
            "content": "",
            "json": None,
            "error": "planner disabled by --no-llm-planner",
            "duration_ms": 0,
            "token_proxy": 0,
        }
    else:
        llm = call_chat_completion(messages, config.get("llm", {}))

    fallback_used = not bool(llm.get("success"))
    fallback_reason = llm.get("error") if fallback_used else None
    source_payload = llm.get("json") if isinstance(llm.get("json"), dict) else {}
    plan = normalize_task_plan(source_payload if not fallback_used else defaults, defaults)
    plan.update({key: value for key, value in extract_content_goals(intent).items() if key not in plan or not plan.get(key)})
    if fallback_used or not plan.get("task_type"):
        plan["task_type"] = detected_task_type

    if explicit_count:
        plan["segment_count_policy"]["target_segments"] = int(explicit_count)
        plan["segment_count_policy"]["max_segments"] = max(int(plan["segment_count_policy"]["max_segments"]), int(explicit_count))

    if not explicit_count and detected_task_type == "highlight_reel":
        plan["task_type"] = "highlight_reel"
        if int(plan["segment_count_policy"].get("target_segments") or 0) < 8:
            plan["segment_count_policy"]["target_segments"] = 12
        plan["segment_count_policy"]["min_segments"] = max(8, int(plan["segment_count_policy"].get("min_segments") or 1))
        plan["segment_count_policy"]["max_segments"] = max(20, int(plan["segment_count_policy"].get("max_segments") or 5))
        plan["duration_policy"]["min_segment_seconds"] = 6.0
        plan["duration_policy"]["max_segment_seconds"] = 18.0
        plan["duration_policy"]["target_segment_seconds"] = plan["duration_policy"].get("target_segment_seconds") or 10.0
        plan["duration_policy"]["max_final_duration_seconds"] = min(float(plan["duration_policy"].get("max_final_duration_seconds") or 240), 240.0)
        plan["selection_policy"]["min_cut_quality_score"] = min(float(plan["selection_policy"].get("min_cut_quality_score") or 0.55), 0.55)
        plan["selection_policy"]["prefer_dense_highlights"] = True
        plan["output_policy"]["transition"] = "short_fade"

    plan["planner_backend"] = "llm_api" if not fallback_used else "default_policy_fallback"
    plan["planner_model"] = llm.get("model")
    plan["planner_token_proxy"] = llm.get("token_proxy")
    plan["user_requested_segment_count"] = int(explicit_count) if explicit_count else None
    plan["forced_segment_count"] = False
    plan["planner_fallback_used"] = fallback_used
    plan["planner_fallback_reason"] = fallback_reason
    plan["planner_prompt_hash"] = prompt_hash

    if raw_response_path:
        raw_response_path.write_text(
            json.dumps(
                {
                    "success": llm.get("success"),
                    "backend": llm.get("backend"),
                    "model": llm.get("model"),
                    "content": llm.get("content", ""),
                    "parsed_json": llm.get("json"),
                    "error": llm.get("error"),
                    "duration_ms": llm.get("duration_ms"),
                    "token_proxy": llm.get("token_proxy"),
                    "prompt_hash": prompt_hash,
                    "fallback_used": fallback_used,
                    "fallback_reason": fallback_reason,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        plan["planner_raw_response_path"] = str(raw_response_path)
    if task_plan_path:
        plan["task_plan_path"] = str(task_plan_path)
        task_plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def build_planner_messages(
    intent: str,
    video_metadata: dict[str, Any],
    subtitle_metadata: dict[str, Any],
    defaults: dict[str, Any],
    constraints: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the LLM planner for ClipPilot-Agent. Return strict JSON only. "
                "Do not select clips. Generate a TaskPlan/ClipPlanPolicy that controls adaptive segment selection."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "intent": intent,
                    "video_metadata": video_metadata,
                    "subtitle_metadata": subtitle_metadata,
                    "defaults": defaults,
                    "user_constraints": constraints,
                    "required_schema": {
                        "task_type": "course_review_summary | highlight_reel | short_video_cut | interview_highlight | tutorial_summary | general",
                        "audience": "...",
                        "output_goal": "first_cut_review_video",
                        "segment_count_policy": {
                            "mode": "adaptive",
                            "min_segments": 1,
                            "max_segments": 20,
                            "target_segments": None,
                            "allow_less_than_target": True,
                        },
                        "duration_policy": {
                            "min_segment_seconds": 6,
                            "max_segment_seconds": 90,
                            "target_segment_seconds": None,
                            "target_final_duration_seconds": None,
                            "max_final_duration_seconds": 240,
                            "allow_shorter_if_quality_low": True,
                        },
                        "selection_policy": {
                            "quality_first": True,
                            "avoid_overlap": True,
                            "avoid_repetition": True,
                            "prefer_semantic_boundary": True,
                            "min_cut_quality_score": 0.6,
                            "prefer_dense_highlights": False,
                        },
                        "output_policy": {
                            "generate_final_review": True,
                            "generate_timeline": True,
                            "generate_subtitle": True,
                            "generate_review_sheet": True,
                            "title_card": "optional",
                            "transition": "none",
                        },
                        "reasoning_summary": "...",
                    },
                    "planner_rules": [
                        "If the user explicitly asks for 3 clips, set target_segments=3.",
                        "If the user asks for a fast-paced highlight reel, quick review rough cut, or says no fixed segment count, use task_type=highlight_reel.",
                        "For highlight_reel, prefer 8-20 micro-clips of 6-18 seconds and do not default to 3 segments.",
                        "If high-quality candidates are insufficient, allow fewer than target instead of forcing low-quality cuts.",
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]


def load_policy_defaults(task_type: str) -> dict[str, Any]:
    path = Path("configs/workflow_policy.yaml")
    if not path.exists():
        return {"task_type": task_type}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    item = data.get(task_type) or data.get("course_review_summary") or {}
    return {
        "task_type": task_type,
        "segment_count_policy": {
            "mode": "adaptive",
            "min_segments": item.get("min_segments", 1),
            "max_segments": item.get("max_segments", 5),
            "target_segments": item.get("target_segments"),
            "allow_less_than_target": item.get("allow_less_than_target", True),
        },
        "duration_policy": {
            "min_segment_seconds": item.get("min_segment_seconds", 20),
            "max_segment_seconds": item.get("max_segment_seconds", 90),
            "target_segment_seconds": item.get("target_segment_seconds"),
            "target_final_duration_seconds": item.get("target_final_duration_seconds"),
            "max_final_duration_seconds": item.get("max_final_duration_seconds", 180),
            "allow_shorter_if_quality_low": item.get("allow_shorter_if_quality_low", True),
        },
        "selection_policy": {
            "quality_first": True,
            "avoid_overlap": True,
            "avoid_repetition": True,
            "prefer_semantic_boundary": True,
            "min_cut_quality_score": item.get("min_cut_quality_score", 0.6),
            "prefer_dense_highlights": item.get("prefer_dense_highlights", False),
        },
        "output_policy": {
            "generate_final_review": True,
            "generate_timeline": True,
            "generate_subtitle": True,
            "generate_review_sheet": True,
            "title_card": "optional",
            "transition": item.get("transition", "none"),
        },
    }


def detect_task_type(intent: str) -> str:
    text = intent.lower()
    if any(term in text for term in ["highlight", "reel", "fast-paced", "quick review", "高光", "粗剪", "快速复习", "节奏紧凑", "不需要固定", "不固定"]):
        return "highlight_reel"
    if any(term in text for term in ["short video", "短视频"]):
        return "short_video_cut"
    if any(term in text for term in ["interview", "访谈"]):
        return "interview_highlight"
    if any(term in text for term in ["tutorial", "step", "教程", "步骤"]):
        return "tutorial_summary"
    if any(term in text for term in ["course", "review", "复习", "课程", "学生"]):
        return "course_review_summary"
    return "general"


def extract_requested_count(intent: str) -> int | None:
    patterns = [
        r"(\d+)\s*(?:clips?|segments?|片段|段)",
        r"剪出\s*(\d+)\s*个",
        r"(一|二|两|三|四|五|六|七|八|九|十)\s*(?:个片段|段|片段)",
        r"剪出\s*(一|二|两|三|四|五|六|七|八|九|十)\s*个",
    ]
    zh = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    for pattern in patterns:
        match = re.search(pattern, intent, flags=re.IGNORECASE)
        if match:
            value = match.group(1)
            return int(value) if value.isdigit() else zh.get(value)
    return None

