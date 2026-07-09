from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from clip_pilot.tools.llm_client import call_chat_completion


DEFAULT_STORYLINE = {
    "storyline_type": "course_review_highlight",
    "target_audience": "students",
    "narrative_goal": "help students quickly review core concepts",
    "recommended_structure": [
        {"role": "hook_or_problem", "needed": True, "description": "Introduce the topic or problem."},
        {"role": "core_concept", "needed": True, "description": "Explain the core concept."},
        {"role": "example", "needed": False, "description": "Use an example if it helps understanding."},
        {"role": "summary", "needed": True, "description": "Summarize the key point."},
    ],
    "selection_rules": {
        "must_be_sentence_complete": True,
        "must_be_semantically_complete": True,
        "avoid_mid_sentence_cut": True,
        "avoid_isolated_pronoun_start": True,
        "avoid_unresolved_reference": True,
        "allow_variable_duration": True,
        "quality_over_count": True,
    },
}


def build_storyline_plan(
    *,
    intent: str,
    video_metadata: dict[str, Any],
    blocks: list[dict[str, Any]],
    config: dict[str, Any],
    output_dir: str,
) -> dict[str, Any]:
    block_summaries = [
        {
            "block_id": block["block_id"],
            "start": block["start"],
            "end": block["end"],
            "block_type": block["block_type"],
            "text_preview": block["text"][:180],
            "completeness_score": block["completeness_score"],
            "standalone_score": block["standalone_score"],
        }
        for block in blocks[:80]
    ]
    messages = [
        {"role": "system", "content": "You are a storyline planner for educational video editing. Return strict JSON only."},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "intent": intent,
                    "video_metadata": video_metadata,
                    "semantic_blocks": block_summaries,
                    "required_output": DEFAULT_STORYLINE,
                    "rules": [
                        "Do not choose exact timestamps.",
                        "Design a coherent storyline before video export.",
                        "Require sentence-complete and semantically complete segments.",
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]
    prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    result = call_chat_completion(messages, config.get("llm", {}))
    if not result.get("success"):
        return {"success": False, "backend": "llm_api", "error": result.get("error")}
    plan = result.get("json") if isinstance(result.get("json"), dict) else {}
    if not plan:
        plan = dict(DEFAULT_STORYLINE)
    plan = {**DEFAULT_STORYLINE, **plan}
    plan["planner_backend"] = "llm_api"
    plan["planner_model"] = result.get("model")
    plan["planner_prompt_hash"] = prompt_hash
    plan["planner_token_proxy"] = result.get("token_proxy")
    root = Path(output_dir)
    raw_path = root / "storyline_planner_raw_response.json"
    plan_path = root / "storyline_plan.json"
    raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
    plan["raw_response_path"] = str(raw_path)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "llm_api", "output_path": str(plan_path), "data": {"storyline_plan": plan, "raw_response_path": str(raw_path), "prompt_hash": prompt_hash}}

