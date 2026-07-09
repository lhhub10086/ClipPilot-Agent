from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from clip_pilot.tools.llm_client import call_chat_completion


def refine_cues_with_llm(
    *,
    raw_cues: list[dict[str, Any]],
    output_dir: str,
    config: dict[str, Any],
    domain_glossary: list[str],
    window_seconds: float = 45.0,
    overlap_cues: int = 1,
    repair_round: int = 0,
) -> dict[str, Any]:
    root = Path(output_dir)
    raw_dir = root / "subtitle_refiner_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cue_map = {cue["cue_id"]: cue for cue in raw_cues}
    windows = _build_windows(raw_cues, window_seconds=window_seconds, overlap_cues=overlap_cues)
    all_units: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    llm_calls = 0
    token_proxy = 0
    fallback_used = False
    errors: list[str] = []

    for idx, window in enumerate(windows, start=1):
        result = _call_refiner_window(
            window=window,
            output_dir=raw_dir,
            config=config,
            domain_glossary=domain_glossary,
            window_index=idx,
            repair_round=repair_round,
        )
        llm_calls += 1
        token_proxy += int(result.get("data", {}).get("token_proxy", 0) or 0)
        if not result.get("success"):
            fallback_used = True
            errors.append(str(result.get("error")))
            units = _rule_units(window)
            unresolved.append({"window_index": idx, "reason": result.get("error", "llm_failed")})
        else:
            units = result["data"]["sentence_units"]
            unresolved.extend(result["data"].get("unresolved_items", []))
        all_units.extend(units)

    units = _dedupe_and_map_units(all_units, cue_map)
    if not units:
        fallback_used = True
        units = _dedupe_and_map_units(_rule_units(raw_cues), cue_map)
    payload = {
        "success": True,
        "backend": "llm_with_rule_preprocess" if fallback_used else "llm",
        "data": {
            "sentence_units": units,
            "unresolved_items": unresolved,
            "llm_called": llm_calls > 0,
            "llm_call_count": llm_calls,
            "token_proxy": token_proxy,
            "fallback_used": fallback_used,
            "errors": errors,
            "model": config.get("llm", {}).get("model", "deepseek-chat"),
        },
    }
    (root / "subtitle_refiner_parsed_response.json").write_text(json.dumps(payload["data"], ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _call_refiner_window(
    *,
    window: list[dict[str, Any]],
    output_dir: Path,
    config: dict[str, Any],
    domain_glossary: list[str],
    window_index: int,
    repair_round: int,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are Subtitle Refiner. Restore Chinese sentence boundaries, punctuation, and obvious ASR corrections. "
                "Never output timestamps. Only reference source cue IDs. Return strict JSON only."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "domain_glossary": domain_glossary,
                    "raw_cues": window,
                    "rules": [
                        "Use only source_cue_ids from raw_cues.",
                        "Do not invent content absent from raw_text.",
                        "Do not output start/end/duration.",
                        "Each sentence unit should contain one complete idea, at most two closely related short clauses.",
                        "Low-confidence corrections must go to unresolved_items.",
                    ],
                    "output_schema": {
                        "sentence_units": [
                            {
                                "source_cue_ids": ["cue_001"],
                                "refined_text": "...",
                                "sentence_complete": True,
                                "corrections": [{"original": "...", "corrected": "...", "reason": "...", "confidence": 0.8}],
                            }
                        ],
                        "unresolved_items": [{"source_cue_id": "cue_001", "raw_text": "...", "reason": "..."}],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    llm_config = dict(config.get("llm", {}))
    llm_config["max_tokens"] = max(int(llm_config.get("max_tokens", 800)), 1800)
    result = call_chat_completion(messages, llm_config)
    raw_path = output_dir / f"subtitle_refiner_raw_window_{window_index:03}_round_{repair_round}.json"
    raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result.get("success"):
        return {"success": False, "backend": "llm_api", "error": result.get("error"), "data": {"raw_response_path": str(raw_path)}}
    parsed = result.get("json") if isinstance(result.get("json"), dict) else {}
    units = parsed.get("sentence_units") if isinstance(parsed.get("sentence_units"), list) else []
    valid_units = []
    allowed = {cue["cue_id"] for cue in window}
    for unit in units:
        if not isinstance(unit, dict):
            continue
        cue_ids = [cue_id for cue_id in unit.get("source_cue_ids", []) if cue_id in allowed]
        if not cue_ids:
            continue
        valid_units.append(
            {
                "source_cue_ids": cue_ids,
                "refined_text": str(unit.get("refined_text", "")).strip(),
                "sentence_complete": bool(unit.get("sentence_complete", True)),
                "corrections": unit.get("corrections", []) if isinstance(unit.get("corrections"), list) else [],
            }
        )
    return {
        "success": bool(valid_units),
        "backend": "llm_api",
        "data": {
            "sentence_units": valid_units,
            "unresolved_items": parsed.get("unresolved_items", []) if isinstance(parsed.get("unresolved_items"), list) else [],
            "raw_response_path": str(raw_path),
            "prompt_hash": prompt_hash,
            "token_proxy": result.get("token_proxy", 0),
            "model": result.get("model"),
        },
        "error": None if valid_units else "subtitle refiner returned no valid sentence units",
    }


def build_semantic_blocks_with_llm(
    *,
    sentence_units: list[dict[str, Any]],
    output_dir: str,
    config: dict[str, Any],
    domain_glossary: list[str],
) -> dict[str, Any]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    blocks = _rule_semantic_blocks(sentence_units)
    payload = {"semantic_blocks": blocks, "backend": "rule_semantic_blocks", "llm_called": False, "model": config.get("llm", {}).get("model", "deepseek-chat")}
    Path(output_dir, "semantic_block_builder_parsed_response.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "rule_semantic_blocks", "data": payload}


def _build_windows(raw_cues: list[dict[str, Any]], window_seconds: float, overlap_cues: int) -> list[list[dict[str, Any]]]:
    windows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    start = None
    for cue in raw_cues:
        if start is None:
            start = float(cue["start"])
        if current and float(cue["end"]) - start > window_seconds:
            windows.append(current)
            current = current[-overlap_cues:] if overlap_cues > 0 else []
            start = float(current[0]["start"]) if current else float(cue["start"])
        current.append(cue)
    if current:
        windows.append(current)
    return windows


def _dedupe_and_map_units(units: list[dict[str, Any]], cue_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    used_keys: set[tuple[str, ...]] = set()
    used_cues: set[str] = set()
    for unit in units:
        cue_ids = [cue_id for cue_id in unit.get("source_cue_ids", []) if cue_id in cue_map]
        if not cue_ids:
            continue
        key = tuple(cue_ids)
        if key in used_keys or any(cue_id in used_cues for cue_id in cue_ids):
            continue
        used_keys.add(key)
        used_cues.update(cue_ids)
        text = str(unit.get("refined_text", "")).strip()
        if not text:
            text = "".join(cue_map[cue_id]["raw_text"] for cue_id in cue_ids).strip()
        confidence_values = [float(item.get("confidence", 0.0)) for item in unit.get("corrections", []) if isinstance(item, dict)]
        output.append(
            {
                "sentence_id": f"sentence_{len(output)+1:04}",
                "start": round(float(cue_map[cue_ids[0]]["start"]), 3),
                "end": round(float(cue_map[cue_ids[-1]]["end"]), 3),
                "duration": round(float(cue_map[cue_ids[-1]]["end"]) - float(cue_map[cue_ids[0]]["start"]), 3),
                "refined_text": text,
                "text": text,
                "original_text": "".join(cue_map[cue_id]["raw_text"] for cue_id in cue_ids),
                "source_cue_ids": cue_ids,
                "corrections": unit.get("corrections", []),
                "correction_confidence": round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None,
                "sentence_complete": bool(unit.get("sentence_complete", True)),
                "timing_source": "raw_asr_cue_boundaries",
            }
        )
    return output


def _rule_units(window: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"source_cue_ids": [cue["cue_id"]], "refined_text": cue["raw_text"], "sentence_complete": True, "corrections": []} for cue in window]


def _rule_semantic_blocks(sentence_units: list[dict[str, Any]], max_duration: float = 45.0) -> list[dict[str, Any]]:
    blocks = []
    current = []
    for unit in sentence_units:
        if current and float(unit["end"]) - float(current[0]["start"]) > max_duration:
            blocks.append(_make_block(len(blocks) + 1, current))
            current = []
        current.append(unit)
        if float(current[-1]["end"]) - float(current[0]["start"]) >= 18.0:
            blocks.append(_make_block(len(blocks) + 1, current))
            current = []
    if current:
        blocks.append(_make_block(len(blocks) + 1, current))
    return blocks


def _make_block(idx: int, units: list[dict[str, Any]]) -> dict[str, Any]:
    text = "".join(unit["refined_text"] for unit in units)
    return {
        "block_id": f"block_{idx:04}",
        "topic": _topic_for_text(text),
        "block_type": _block_type_for_text(text),
        "sentence_ids": [unit["sentence_id"] for unit in units],
        "start": units[0]["start"],
        "end": units[-1]["end"],
        "duration": round(float(units[-1]["end"]) - float(units[0]["start"]), 3),
        "text": text,
        "summary": text[:80],
    }


def _topic_for_text(text: str) -> str:
    if "加速度" in text:
        return "加速度"
    if "初中物理" in text or "高中物理" in text:
        return "初高中物理衔接"
    if "学习" in text or "练习" in text:
        return "学习方法"
    return "课程内容"


def _block_type_for_text(text: str) -> str:
    if "第一个" in text or "第二个" in text or "第三个" in text:
        return "introduction"
    if "例" in text or "题" in text:
        return "example"
    if "总结" in text or "最后" in text:
        return "conclusion"
    return "explanation"

