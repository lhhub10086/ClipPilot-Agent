from __future__ import annotations

import json
from typing import Any

from clip_pilot.tools.llm_client import call_chat_completion


def generate_content(intent: str, selected: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    llm_config = dict(config.get("llm", {}))
    llm_config["max_tokens"] = max(int(llm_config.get("max_tokens", 800)), 1800)
    messages = [
        {"role": "system", "content": "You are ClipPilot-Agent. Return strict JSON only as {\"clips\":[...]}."},
        {
            "role": "user",
            "content": (
                f"Intent: {intent}\n"
                "For every selected candidate, return one item with clip_id, title, reason, review_question, clip_suggestion. "
                "Do not skip any clip_id.\n"
                f"Candidates: {json.dumps(selected, ensure_ascii=False)}"
            ),
        },
    ]
    result = call_chat_completion(messages, llm_config)
    if not result.get("success"):
        return {"success": False, "backend": "llm_api", "error": result.get("error")}
    parsed = extract_clip_items(result.get("json"))
    if parsed is None:
        return {"success": False, "backend": "llm_api", "error": "LLM output must be a JSON array"}
    by_id = map_generated_items(parsed, selected)
    missing_ids = [item["clip_id"] for item in selected if missing_fields(by_id.get(item["clip_id"], {}))]
    if missing_ids:
        repaired = repair_missing(intent, [item for item in selected if item["clip_id"] in missing_ids], llm_config)
        if not repaired.get("success"):
            return repaired
        by_id.update(repaired["data"]["by_id"])
    clips = []
    for item in selected:
        gen = by_id.get(item["clip_id"], {})
        missing = missing_fields(gen)
        if missing:
            return {"success": False, "backend": "llm_api", "error": f"missing {missing} for {item['clip_id']}"}
        clips.append(
            {
                "clip_id": item["clip_id"],
                "start": item["start"],
                "end": item["end"],
                "duration": item["duration"],
                "title": str(gen["title"]),
                "reason": str(gen["reason"]),
                "review_question": str(gen["review_question"]),
                "clip_suggestion": str(gen["clip_suggestion"]),
                "transcript_evidence": item["transcript"],
                "score": item.get("score", 0.0),
                "cut_quality_score": item.get("cut_quality_score", item.get("score", 0.0)),
                "original_start": item.get("original_start", item.get("start")),
                "original_end": item.get("original_end", item.get("end")),
                "refined_start": item.get("refined_start", item.get("start")),
                "refined_end": item.get("refined_end", item.get("end")),
                "boundary_refined": item.get("boundary_refined", False),
                "duplicate_ratio": item.get("duplicate_ratio", 0.0),
                "selection_reason": item.get("selection_reason", ""),
                "generated_content": {"backend": "llm_api", "llm_model": result.get("model"), "token_proxy": result.get("token_proxy"), "llm_error": None},
            }
        )
    return {"success": True, "backend": "llm_api", "data": {"clips": clips, "selected_count": len(clips)}}


def extract_clip_items(parsed: Any) -> list[dict[str, Any]] | None:
    if isinstance(parsed, dict):
        parsed = parsed.get("clips") or parsed.get("items")
    if not isinstance(parsed, list):
        return None
    return [item for item in parsed if isinstance(item, dict)]


def map_generated_items(items: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id = {str(item.get("clip_id")): item for item in items if item.get("clip_id")}
    if len(items) == len(selected):
        for generated, source in zip(items, selected):
            by_id.setdefault(source["clip_id"], generated)
    return by_id


def missing_fields(item: dict[str, Any]) -> list[str]:
    return [key for key in ["title", "reason", "review_question", "clip_suggestion"] if not item.get(key)]


def repair_missing(intent: str, selected: list[dict[str, Any]], llm_config: dict[str, Any]) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": "Return strict JSON only as {\"clips\":[...]}. Fill every requested clip_id."},
        {
            "role": "user",
            "content": (
                f"Intent: {intent}\n"
                "Generate missing content for these clips. Required fields: clip_id, title, reason, review_question, clip_suggestion.\n"
                f"Clips: {json.dumps(selected, ensure_ascii=False)}"
            ),
        },
    ]
    result = call_chat_completion(messages, llm_config)
    if not result.get("success"):
        return {"success": False, "backend": "llm_api", "error": result.get("error")}
    items = extract_clip_items(result.get("json"))
    if items is None:
        return {"success": False, "backend": "llm_api", "error": "LLM repair output must be a JSON array"}
    return {"success": True, "backend": "llm_api", "data": {"by_id": map_generated_items(items, selected)}}

