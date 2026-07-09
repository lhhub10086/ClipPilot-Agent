from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from clip_pilot.tools.llm_client import call_chat_completion


def run_timeline_editor(
    *,
    intent: str,
    selector_response: dict[str, Any],
    semantic_blocks: list[dict[str, Any]],
    default_policy: dict[str, Any],
    config: dict[str, Any],
    output_dir: str,
    output_name: str = "editor_timeline.json",
) -> dict[str, Any]:
    block_map = {block["block_id"]: block for block in semantic_blocks}
    messages = [
        {
            "role": "system",
            "content": (
                "You are Timeline Editor. Organize a coherent rough-cut timeline from selected semantic blocks. "
                "Use complete blocks only. Do not cut sentences. Return strict JSON only."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_intent": intent,
                    "selector_response": selector_response,
                    "semantic_blocks": [
                        {
                            "block_id": block["block_id"],
                            "start": block["start"],
                            "end": block["end"],
                            "duration": block["duration"],
                            "text": block["text"],
                            "block_type": block["block_type"],
                            "completeness_score": block.get("completeness_score", 0.8),
                            "standalone_score": block.get("standalone_score", 0.8),
                            "contains_unresolved_asr": bool(block.get("contains_unresolved_asr", False)),
                            "unresolved_sentence_ids": block.get("unresolved_sentence_ids", []),
                            "safe_for_auto_edit": bool(block.get("safe_for_auto_edit", True)),
                        }
                        for block in semantic_blocks
                    ],
                    "default_policy": default_policy,
                    "output_schema": {
                        "timeline_items": [
                            {
                                "segment_id": "segment_001",
                                "role": "hook | core_concept | explanation | example | summary | bridge",
                                "source_block_ids": ["block_001"],
                                "why_included": "...",
                                "bridge_before": None,
                                "bridge_after": "The next segment explains the previous concept with an example.",
                                "expected_viewer_understanding": "...",
                            }
                        ],
                        "editing_strategy": {
                            "mode": "single_topic | highlight_reel",
                            "reason": "...",
                            "quality_over_count": True,
                            "allow_variable_segment_duration": True,
                        },
                    },
                    "rules": [
                        "Use only source_block_ids that exist.",
                        "Do not use partial blocks or custom timestamps.",
                        "Do not include transcript, source_start, or source_end; the system will derive them from source_block_ids.",
                        "Prefer single_topic for course review unless multiple topics need bridge text.",
                        "No isolated topic jumps without bridge_before or bridge_after.",
                        "Quality over count: fewer coherent segments are better than many fragments.",
                        "Return at most 5 timeline_items.",
                        "Keep why_included and expected_viewer_understanding concise.",
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]
    prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    llm_config = dict(config.get("llm", {}))
    llm_config["max_tokens"] = max(int(llm_config.get("max_tokens", 800)), 1800)
    result = call_chat_completion(messages, llm_config)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    raw_path = root / output_name.replace(".json", "_raw_response.json")
    if not result.get("success"):
        raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": False, "backend": "llm_api", "error": result.get("error")}
    parsed = result.get("json") if isinstance(result.get("json"), dict) else {}
    if not isinstance(parsed.get("timeline_items"), list):
        return {"success": False, "backend": "llm_api", "error": "editor output missing timeline_items"}
    normalized = normalize_editor_timeline(parsed, block_map)
    parsed_path = root / output_name
    raw_path.write_text(json.dumps({**result, "prompt_hash": prompt_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
    parsed_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "backend": "llm_api",
        "output_path": str(parsed_path),
        "data": {
            "editor_timeline": normalized,
            "raw_response_path": str(raw_path),
            "parsed_response_path": str(parsed_path),
            "prompt_hash": prompt_hash,
            "model": result.get("model"),
            "segment_count": len(normalized.get("timeline_items", [])),
        },
    }


def normalize_editor_timeline(payload: dict[str, Any], block_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    items = []
    used = set()
    for idx, item in enumerate(payload.get("timeline_items", []), start=1):
        ids = [block_id for block_id in item.get("source_block_ids", []) if block_id in block_map]
        if not ids:
            continue
        blocks = [block_map[block_id] for block_id in ids]
        start = min(float(block["start"]) for block in blocks)
        end = max(float(block["end"]) for block in blocks)
        text = " ".join(block["text"] for block in sorted(blocks, key=lambda b: float(b["start"]))).strip()
        segment_id = item.get("segment_id") or f"segment_{len(items)+1:03}"
        if segment_id in used:
            segment_id = f"segment_{len(items)+1:03}"
        used.add(segment_id)
        items.append(
            {
                "segment_id": segment_id,
                "role": item.get("role", "core_concept"),
                "source_block_ids": ids,
                "source_start": round(start, 3),
                "source_end": round(end, 3),
                "duration": round(end - start, 3),
                "transcript": text,
                "why_included": item.get("why_included", "Selected by Timeline Editor from complete semantic blocks."),
                "bridge_before": item.get("bridge_before"),
                "bridge_after": item.get("bridge_after"),
                "expected_viewer_understanding": item.get("expected_viewer_understanding", ""),
            }
        )
    items.sort(key=lambda value: float(value["source_start"]))
    return {
        "timeline_items": items,
        "editing_strategy": payload.get(
            "editing_strategy",
            {"mode": "highlight_reel", "reason": "Normalized editor output.", "quality_over_count": True, "allow_variable_segment_duration": True},
        ),
    }

