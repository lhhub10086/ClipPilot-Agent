from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from clip_pilot.tools.llm_client import call_chat_completion


def resolve_transcripts(
    *,
    sentence_units_path: str,
    semantic_blocks_path: str,
    recovery_path: str,
    output_dir: str,
    config: dict[str, Any],
    glossary: list[str],
) -> dict[str, Any]:
    units = json.loads(Path(sentence_units_path).read_text(encoding="utf-8")).get("sentence_units", [])
    blocks = json.loads(Path(semantic_blocks_path).read_text(encoding="utf-8")).get("semantic_blocks", [])
    recoveries = json.loads(Path(recovery_path).read_text(encoding="utf-8")).get("recoveries", [])
    unit_map = {unit["sentence_id"]: unit for unit in units}
    block_by_sentence = {}
    for block in blocks:
        for sid in block.get("sentence_ids", []):
            block_by_sentence[sid] = block
    resolutions = []
    updated = {unit["sentence_id"]: dict(unit) for unit in units}
    for recovery in recoveries:
        sid = recovery.get("sentence_id")
        if sid not in unit_map:
            continue
        idx = next((i for i, unit in enumerate(units) if unit["sentence_id"] == sid), -1)
        previous_text = units[idx - 1]["refined_text"] if idx > 0 else ""
        next_text = units[idx + 1]["refined_text"] if 0 <= idx < len(units) - 1 else ""
        block = block_by_sentence.get(sid, {})
        result = resolve_one(
            original=unit_map[sid],
            recovery=recovery,
            previous_text=previous_text,
            next_text=next_text,
            block=block,
            config=config,
            glossary=glossary,
            output_dir=output_dir,
        )
        resolutions.append(result)
        if result.get("resolution_status") == "resolved" and result.get("changed") and float(result.get("confidence", 0.0)) >= 0.75:
            updated[sid]["refined_text"] = result["selected_text"]
            updated[sid]["text"] = result["selected_text"]
            updated[sid].setdefault("corrections", []).append({"original": unit_map[sid]["refined_text"], "corrected": result["selected_text"], "reason": result.get("reason", ""), "confidence": result.get("confidence")})
    updated_units = list(updated.values())
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    resolution_path = root / "transcript_resolution.json"
    recovered_units_path = root / "sentence_units_recovered.json"
    resolution_path.write_text(json.dumps({"resolutions": resolutions}, ensure_ascii=False, indent=2), encoding="utf-8")
    recovered_units_path.write_text(json.dumps({"sentence_units": updated_units}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "backend": "llm_transcript_resolver",
        "output_path": str(resolution_path),
        "data": {
            "resolutions": resolutions,
            "sentence_units": updated_units,
            "recovered_units_path": str(recovered_units_path),
            "resolved_count": sum(1 for item in resolutions if item.get("resolution_status") == "resolved"),
            "unresolved_count": sum(1 for item in resolutions if item.get("resolution_status") != "resolved"),
        },
    }


def resolve_one(
    *,
    original: dict[str, Any],
    recovery: dict[str, Any],
    previous_text: str,
    next_text: str,
    block: dict[str, Any],
    config: dict[str, Any],
    glossary: list[str],
    output_dir: str,
) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": "You are Transcript Resolver. Select a corrected subtitle only when supported by ASR/OCR candidates or strong context. Return strict JSON only."},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "physics_glossary": glossary,
                    "original_asr": original.get("refined_text"),
                    "local_re_asr_candidates": recovery.get("recovered_candidates", []),
                    "previous_sentence": previous_text,
                    "next_sentence": next_text,
                    "semantic_block_topic": block.get("topic"),
                    "rules": [
                        "Do not invent original speech.",
                        "If confidence < 0.75, keep unresolved.",
                        "Use at least one ASR candidate or strong local context.",
                    ],
                    "output_schema": {
                        "sentence_id": original.get("sentence_id"),
                        "selected_text": "...",
                        "resolution_status": "resolved | unresolved",
                        "confidence": 0.0,
                        "evidence_sources": [],
                        "reason": "...",
                        "changed": False,
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    result = call_chat_completion(messages, dict(config.get("llm", {})))
    raw_dir = Path(output_dir) / "resolver_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{original.get('sentence_id')}_{prompt_hash}.json"
    raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result.get("success") or not isinstance(result.get("json"), dict):
        return _unresolved(original, f"resolver_llm_failed: {result.get('error')}", str(raw_path))
    parsed = result["json"]
    confidence = float(parsed.get("confidence", 0.0) or 0.0)
    status = parsed.get("resolution_status", "unresolved")
    candidate_texts = [item.get("text", "") for item in recovery.get("recovered_candidates", []) if item.get("text")]
    selected = str(parsed.get("selected_text") or original.get("refined_text") or "")
    has_evidence = any(selected and selected in text or text and text in selected for text in candidate_texts) or confidence >= 0.85
    if status != "resolved" or confidence < 0.75 or not has_evidence:
        return _unresolved(original, parsed.get("reason", "insufficient evidence"), str(raw_path), confidence=confidence)
    return {
        "sentence_id": original.get("sentence_id"),
        "selected_text": selected,
        "resolution_status": "resolved",
        "confidence": confidence,
        "evidence_sources": parsed.get("evidence_sources", ["local_asr", "context"]),
        "reason": parsed.get("reason", ""),
        "changed": selected != original.get("refined_text"),
        "raw_response_path": str(raw_path),
    }


def _unresolved(original: dict[str, Any], reason: str, raw_response_path: str, confidence: float = 0.0) -> dict[str, Any]:
    return {
        "sentence_id": original.get("sentence_id"),
        "selected_text": original.get("refined_text"),
        "resolution_status": "unresolved",
        "confidence": confidence,
        "evidence_sources": [],
        "reason": reason,
        "changed": False,
        "raw_response_path": raw_response_path,
    }

