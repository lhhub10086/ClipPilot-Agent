from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from clip_pilot.tools.llm_client import call_chat_completion


def run_content_selector(*, intent: str, video_metadata: dict[str, Any], semantic_blocks: list[dict[str, Any]], config: dict[str, Any], output_dir: str) -> dict[str, Any]:
    block_inputs = [
        {
            "block_id": block["block_id"],
            "start": block["start"],
            "end": block["end"],
            "text": block["text"],
            "block_type": block["block_type"],
            "completeness_score": block.get("completeness_score", 0.8),
            "standalone_score": block.get("standalone_score", 0.8),
            "contains_unresolved_asr": bool(block.get("contains_unresolved_asr", False)),
            "unresolved_sentence_ids": block.get("unresolved_sentence_ids", []),
            "lexical_risk_score": block.get("lexical_risk_score", 0.0),
            "lexical_risk_level": block.get("lexical_risk_level", "low_risk"),
            "narrative_importance": block.get("narrative_importance", 0.0),
            "bridge_importance": block.get("bridge_importance", 0.0),
            "safe_alternative_ids": block.get("safe_alternative_ids", []),
            "required_for_coherence": block.get("required_for_coherence", False),
            "review_if_selected": block.get("review_if_selected", False),
            "safe_for_auto_edit": bool(block.get("safe_for_auto_edit", True)),
        }
        for block in semantic_blocks
    ]
    block_by_id = {block.get("block_id"): block for block in semantic_blocks}
    messages = [
        {
            "role": "system",
            "content": (
                "You are Content Selector, one agent in a video editing workflow. "
                "Only select meaningful course-review content. Do not build a timeline. Return strict JSON only."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_intent": intent,
                    "video_metadata": video_metadata,
                    "semantic_blocks": block_inputs,
                    "output_schema": {
                        "selected_topics": [
                            {
                                "topic_id": "topic_001",
                                "topic_title": "...",
                                "importance_reason": "...",
                                "candidate_block_ids": ["block_001"],
                                "priority": 1,
                            }
                        ],
                        "discarded_blocks": [{"block_id": "...", "reason": "filler / transition / weak standalone value"}],
                        "excluded_due_to_asr_risk": [{"block_id": "...", "reason": "contains unresolved ASR"}],
                        "selected_scope_unresolved_sentence_ids": [],
                        "requires_manual_review": False,
                        "candidate_scores": [
                            {
                                "block_id": "...",
                                "importance_score": 0.0,
                                "topic_consistency_score": 0.0,
                                "context_completeness_score": 0.0,
                                "storyline_contribution_score": 0.0,
                                "lexical_risk_penalty": 0.0,
                                "duplication_penalty": 0.0,
                                "duration_penalty": 0.0,
                                "selection_score": 0.0,
                            }
                        ],
                    },
                    "rules": [
                        "Do not select filler or pure transition blocks.",
                        "Do not select blocks with weak standalone value.",
                        "Treat lexical risk as a penalty, not an unconditional ban.",
                        "low_risk blocks can be selected directly.",
                        "medium_risk blocks should use safe alternatives first; if needed for coherence, mark review_if_selected.",
                        "high_risk blocks are excluded unless manually confirmed as a key bridge.",
                        "If a risky block is essential for coherence, set requires_manual_review=true and list selected_scope_unresolved_sentence_ids.",
                        "Prefer groups of adjacent blocks that form a complete knowledge point.",
                        "Do not decide exact cuts or order beyond topic priority.",
                        "Return at most 4 selected_topics.",
                        "For each topic, return at most 8 candidate_block_ids.",
                        "discarded_blocks is only for representative examples; return at most 20 discarded_blocks.",
                        "Do not list every discarded block.",
                        "Keep every reason under 30 Chinese characters or 20 English words.",
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]
    prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    llm_config = dict(config.get("llm", {}))
    llm_config["max_tokens"] = max(int(llm_config.get("max_tokens", 800)), 2400)
    result = call_chat_completion(messages, llm_config)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    raw_path = root / "selector_raw_response.json"
    if not result.get("success"):
        raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": False, "backend": "llm_api", "error": result.get("error")}
    parsed = result.get("json") if isinstance(result.get("json"), dict) else {}
    if not isinstance(parsed.get("selected_topics"), list):
        return {"success": False, "backend": "llm_api", "error": "selector output missing selected_topics"}
    parsed.setdefault("discarded_blocks", [])
    parsed.setdefault("excluded_due_to_asr_risk", [])
    parsed.setdefault("candidate_scores", [])
    parsed["selected_topics"] = parsed["selected_topics"][:4]
    for topic in parsed["selected_topics"]:
        if isinstance(topic, dict) and isinstance(topic.get("candidate_block_ids"), list):
            topic["candidate_block_ids"] = topic["candidate_block_ids"][:8]
    if isinstance(parsed.get("discarded_blocks"), list):
        parsed["discarded_blocks"] = parsed["discarded_blocks"][:20]
    selected_block_ids = {
        block_id
        for topic in parsed.get("selected_topics", [])
        for block_id in topic.get("candidate_block_ids", [])
    }
    selected_unresolved: list[str] = []
    excluded_due_to_asr_risk: list[dict[str, str]] = list(parsed.get("excluded_due_to_asr_risk") or [])
    for block_id, block in block_by_id.items():
        unresolved = block.get("unresolved_sentence_ids", [])
        if block_id in selected_block_ids and unresolved:
            selected_unresolved.extend(str(sid) for sid in unresolved)
        elif block_id not in selected_block_ids and block.get("contains_unresolved_asr"):
            excluded_due_to_asr_risk.append({"block_id": str(block_id), "reason": "contains unresolved ASR; safer alternatives preferred"})
    scored_ids = {item.get("block_id") for item in parsed.get("candidate_scores", []) if isinstance(item, dict)}
    for block_id in selected_block_ids:
        block = block_by_id.get(block_id, {})
        if block_id not in scored_ids:
            parsed["candidate_scores"].append(_score_block(block))
    parsed["selected_scope_unresolved_sentence_ids"] = sorted(set(selected_unresolved))
    parsed["requires_manual_review"] = bool(parsed["selected_scope_unresolved_sentence_ids"])
    parsed["excluded_due_to_asr_risk"] = excluded_due_to_asr_risk[:20]
    parsed_path = root / "selector_response.json"
    raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
    parsed_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "backend": "llm_api",
        "output_path": str(parsed_path),
        "data": {
            "selector_response": parsed,
            "raw_response_path": str(raw_path),
            "parsed_response_path": str(parsed_path),
            "prompt_hash": prompt_hash,
            "model": result.get("model"),
            "selected_count": len(parsed.get("selected_topics", [])),
        },
    }


def _score_block(block: dict[str, Any]) -> dict[str, Any]:
    duration = float(block.get("duration", 0.0) or 0.0)
    importance = float(block.get("narrative_importance", 0.5) or 0.5)
    storyline = max(float(block.get("bridge_importance", 0.0) or 0.0), importance * 0.7)
    risk_penalty = float(block.get("lexical_risk_score", 0.0) or 0.0)
    duration_penalty = 0.2 if duration > 80 or duration < 5 else 0.0
    selection_score = importance + 0.8 * storyline + 0.7 * importance + 0.6 * storyline - risk_penalty - duration_penalty
    return {
        "block_id": block.get("block_id"),
        "importance_score": round(importance, 3),
        "topic_consistency_score": round(importance, 3),
        "context_completeness_score": round(importance, 3),
        "storyline_contribution_score": round(storyline, 3),
        "lexical_risk_penalty": round(risk_penalty, 3),
        "duplication_penalty": 0.0,
        "duration_penalty": round(duration_penalty, 3),
        "selection_score": round(selection_score, 3),
    }

