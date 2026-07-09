from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from clip_pilot.tools.llm_client import call_chat_completion


def run_coherence_judge(
    *,
    intent: str,
    editor_timeline: dict[str, Any],
    transcript_markdown: str,
    config: dict[str, Any],
    output_dir: str,
    round_index: int = 1,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are Coherence Judge, a strict video transcript reviewer. "
                "Judge whether the rough-cut transcript is coherent enough to export. Return strict JSON only."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_intent": intent,
                    "editor_timeline": editor_timeline,
                    "final_review_transcript_md": transcript_markdown,
                    "passing_criteria": {
                        "passed": True,
                        "score_minimum": 0.75,
                        "no_major_topic_jump": True,
                        "no_mid_sentence_cut": True,
                        "no_missing_context": True,
                    },
                    "output_schema": {
                        "passed": False,
                        "score": 0.0,
                        "reason": "...",
                        "major_problems": [
                            {
                                "type": "topic_jump | mid_sentence_cut | missing_context | weak_transition | duplicate | incoherent_order",
                                "location": "between segment_002 and segment_003",
                                "problem": "...",
                                "repair_action": "drop_segment | expand_context | insert_bridge | reorder | switch_to_single_topic",
                            }
                        ],
                        "segment_feedback": [
                            {
                                "segment_id": "segment_001",
                                "keep": True,
                                "reason": "...",
                                "needs_expand_before": False,
                                "needs_expand_after": False,
                            }
                        ],
                        "repair_instruction": {
                            "drop_segments": [],
                            "expand_segments": [],
                            "insert_bridges": [],
                            "switch_to_single_topic": False,
                        },
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    llm_config = dict(config.get("llm", {}))
    llm_config["max_tokens"] = max(int(llm_config.get("max_tokens", 800)), 1600)
    result = call_chat_completion(messages, llm_config)
    root = Path(output_dir)
    raw_path = root / f"judge_raw_response_round_{round_index}.json"
    if not result.get("success"):
        raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": False, "backend": "llm_api", "error": result.get("error")}
    parsed = normalize_judge_response(result.get("json") if isinstance(result.get("json"), dict) else {})
    parsed_path = root / f"judge_response_round_{round_index}.json"
    raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
    parsed_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "backend": "llm_api",
        "output_path": str(parsed_path),
        "data": {
            "judge_response": parsed,
            "raw_response_path": str(raw_path),
            "parsed_response_path": str(parsed_path),
            "prompt_hash": prompt_hash,
            "model": result.get("model"),
            "score": parsed.get("score"),
            "repair_round": round_index,
        },
    }


def normalize_judge_response(payload: dict[str, Any]) -> dict[str, Any]:
    score = float(payload.get("score", 0.0) or 0.0)
    major = payload.get("major_problems") if isinstance(payload.get("major_problems"), list) else []
    passed = bool(payload.get("passed")) and score >= 0.75 and not major
    repair = payload.get("repair_instruction") if isinstance(payload.get("repair_instruction"), dict) else {}
    return {
        "passed": passed,
        "score": max(0.0, min(1.0, score)),
        "reason": str(payload.get("reason", "")),
        "major_problems": major,
        "segment_feedback": payload.get("segment_feedback") if isinstance(payload.get("segment_feedback"), list) else [],
        "repair_instruction": {
            "drop_segments": repair.get("drop_segments", []),
            "expand_segments": repair.get("expand_segments", []),
            "insert_bridges": repair.get("insert_bridges", []),
            "switch_to_single_topic": bool(repair.get("switch_to_single_topic", False)),
        },
    }

