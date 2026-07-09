from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from clip_pilot.tools.llm_client import call_chat_completion


def judge_subtitle_quality(
    *,
    raw_cues: list[dict[str, Any]],
    sentence_units: list[dict[str, Any]],
    semantic_blocks: list[dict[str, Any]],
    domain_glossary: list[str],
    output_dir: str,
    config: dict[str, Any],
    repair_round: int = 0,
) -> dict[str, Any]:
    metrics = _metrics(sentence_units)
    sample_units = sentence_units[:40]
    messages = [
        {"role": "system", "content": "You are Subtitle Quality Judge. Check whether refined Chinese subtitles are suitable as video editing boundaries. Return strict JSON only."},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "domain_glossary": domain_glossary,
                    "metrics": metrics,
                    "raw_cue_sample": raw_cues[:40],
                    "sentence_unit_sample": sample_units,
                    "semantic_block_sample": semantic_blocks[:10],
                    "criteria": {
                        "not_overmerged": True,
                        "not_fragmented": True,
                        "time_from_raw_cues": True,
                        "suitable_for_cut_boundaries": True,
                    },
                    "output_schema": {"passed": True, "score": 0.0, "problems": [], "repair_instructions": []},
                },
                ensure_ascii=False,
            ),
        },
    ]
    prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    llm_config = dict(config.get("llm", {}))
    llm_config["max_tokens"] = max(int(llm_config.get("max_tokens", 800)), 1200)
    result = call_chat_completion(messages, llm_config)
    root = Path(output_dir)
    raw_path = root / f"subtitle_judge_raw_response_round_{repair_round}.json"
    raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
    if result.get("success") and isinstance(result.get("json"), dict):
        parsed = result["json"]
    else:
        parsed = _rule_judge(metrics, error=result.get("error"))
    normalized = {
        "passed": bool(parsed.get("passed")) and float(parsed.get("score", 0.0) or 0.0) >= 0.75,
        "score": max(0.0, min(1.0, float(parsed.get("score", 0.0) or 0.0))),
        "problems": parsed.get("problems", []) if isinstance(parsed.get("problems"), list) else [],
        "repair_instructions": parsed.get("repair_instructions", []) if isinstance(parsed.get("repair_instructions"), list) else [],
        "metrics": metrics,
        "model": result.get("model"),
        "backend": "llm_api" if result.get("success") else "rule_fallback",
        "prompt_hash": prompt_hash,
        "raw_response_path": str(raw_path),
    }
    parsed_path = root / f"subtitle_judge_response_round_{repair_round}.json"
    parsed_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": normalized["backend"], "output_path": str(parsed_path), "data": {"judge_response": normalized}}


def _metrics(sentence_units: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [float(unit.get("duration", 0.0)) for unit in sentence_units]
    over_15 = sum(1 for item in durations if item > 15) / len(durations) if durations else 1.0
    under_3 = sum(1 for item in durations if item < 3) / len(durations) if durations else 1.0
    multi = sum(1 for unit in sentence_units if _multi_thought(unit.get("refined_text", ""))) / len(sentence_units) if sentence_units else 1.0
    complete = sum(1 for unit in sentence_units if unit.get("sentence_complete")) / len(sentence_units) if sentence_units else 0.0
    return {
        "sentence_unit_count": len(sentence_units),
        "avg_sentence_duration": round(sum(durations) / len(durations), 3) if durations else 0.0,
        "sentence_over_15s_ratio": round(over_15, 3),
        "sentence_under_3s_ratio": round(under_3, 3),
        "multi_thought_sentence_ratio": round(multi, 3),
        "sentence_completeness_score": round(complete, 3),
    }


def _multi_thought(text: str) -> bool:
    markers = ["第一个", "第二个", "第三个", "首先", "然后", "接下来", "最后"]
    return sum(1 for marker in markers if marker in text) >= 2


def _rule_judge(metrics: dict[str, Any], error: str | None = None) -> dict[str, Any]:
    problems = []
    if metrics["sentence_over_15s_ratio"] >= 0.1:
        problems.append({"type": "overmerged", "detail": "too many sentence units over 15 seconds"})
    if metrics["sentence_under_3s_ratio"] >= 0.5:
        problems.append({"type": "fragmented", "detail": "too many sentence units under 3 seconds"})
    if metrics["multi_thought_sentence_ratio"] >= 0.1:
        problems.append({"type": "multi_thought", "detail": "too many units contain multiple independent ideas"})
    if error:
        problems.append({"type": "llm_error", "detail": error})
    score = 1.0 - min(0.8, len(problems) * 0.2)
    return {"passed": not problems and score >= 0.75, "score": score, "problems": problems, "repair_instructions": []}

