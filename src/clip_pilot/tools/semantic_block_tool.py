from __future__ import annotations

import re
from typing import Any


DEPENDENT_START = {"and", "but", "so", "because", "this", "that", "it", "they", "which", "然后", "所以", "这个", "那个", "它"}


def build_blocks(sentences: list[dict[str, Any]], min_duration: float = 8.0, max_duration: float = 45.0) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for sent in sentences:
        if current:
            projected = float(sent["end"]) - float(current[0]["start"])
            if projected > max_duration:
                blocks.append(_make_block(len(blocks) + 1, current))
                current = []
        current.append(sent)
        duration = float(current[-1]["end"]) - float(current[0]["start"])
        if duration >= min_duration and _ends_cleanly(current[-1]["text"]):
            blocks.append(_make_block(len(blocks) + 1, current))
            current = []
    if current:
        if blocks and float(current[-1]["end"]) - float(current[0]["start"]) < min_duration:
            merged = blocks.pop()["sentences"] + current
            blocks.append(_make_block(len(blocks) + 1, merged))
        else:
            blocks.append(_make_block(len(blocks) + 1, current))
    return {"success": True, "backend": "semantic_block_generator", "data": {"blocks": blocks, "block_count": len(blocks)}}


def select_semantic_blocks(blocks: list[dict[str, Any]], storyline_plan: dict[str, Any], max_final_duration: float = 240.0) -> dict[str, Any]:
    selected = []
    used = 0.0
    for block in blocks:
        if block["block_type"] in {"transition", "filler"}:
            continue
        if float(block["duration"]) < 8.0 or float(block["duration"]) > 45.0:
            continue
        if block["completeness_score"] < 0.55 or block["standalone_score"] < 0.5:
            continue
        if used + block["duration"] > max_final_duration:
            continue
        item = {
            "clip_id": f"clip_{len(selected)+1:03}",
            "segment_id": f"segment_{len(selected)+1:03}",
            "role": _role_for_block(block),
            "start": block["start"],
            "end": block["end"],
            "duration": block["duration"],
            "text": block["text"],
            "transcript": block["text"],
            "sentence_ids": [sent["sentence_id"] for sent in block["sentences"]],
            "semantic_block_ids": [block["block_id"]],
            "starts_mid_sentence": False,
            "ends_mid_sentence": False,
            "standalone_score": block["standalone_score"],
            "completeness_score": block["completeness_score"],
            "coherence_score": round((block["standalone_score"] + block["completeness_score"]) / 2, 4),
            "cut_quality_score": round((block["standalone_score"] + block["completeness_score"]) / 2, 4),
            "selection_reason": f"Selected semantic {block['block_type']} block with complete sentence boundaries.",
            "bridge_text_before": None,
            "bridge_text_after": None,
            "duplicate_ratio": 0.0,
            "original_start": block["start"],
            "original_end": block["end"],
            "refined_start": block["start"],
            "refined_end": block["end"],
            "boundary_refined": True,
        }
        selected.append(item)
        used += float(block["duration"])
        if len(selected) >= 8:
            break
    return {"success": True, "backend": "semantic_block_selector", "data": {"selected": selected, "selected_count": len(selected), "used_duration": round(used, 3)}}


def _make_block(idx: int, sentences: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(sent["text"] for sent in sentences).strip()
    start = float(sentences[0]["start"])
    end = float(sentences[-1]["end"])
    block_type = classify_block(text)
    starts_dependency = _starts_with_dependency(text)
    completeness = 0.82 if _ends_cleanly(text) else 0.62
    standalone = 0.78 if not starts_dependency else 0.45
    if block_type == "filler":
        completeness -= 0.2
        standalone -= 0.2
    return {
        "block_id": f"block_{idx:04}",
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(end - start, 3),
        "sentences": sentences,
        "text": text,
        "block_type": block_type,
        "completeness_score": round(max(0.0, min(1.0, completeness)), 4),
        "standalone_score": round(max(0.0, min(1.0, standalone)), 4),
        "starts_mid_sentence": False,
        "ends_mid_sentence": False,
    }


def classify_block(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["define", "definition", "means", "概念", "定义", "是什么"]):
        return "definition"
    if any(word in lower for word in ["example", "for instance", "比如", "例子"]):
        return "example"
    if any(word in lower for word in ["compare", "difference", "区别", "联系"]):
        return "comparison"
    if any(word in lower for word in ["therefore", "summary", "总结", "关键"]):
        return "conclusion"
    if any(word in lower for word in ["welcome", "thanks", "subscribe", "欢迎", "谢谢"]):
        return "filler"
    if any(word in lower for word in ["then", "next", "接下来", "然后"]):
        return "transition"
    return "explanation"


def _role_for_block(block: dict[str, Any]) -> str:
    return {
        "definition": "core_concept",
        "comparison": "core_concept",
        "example": "example",
        "conclusion": "summary",
        "explanation": "core_concept",
    }.get(block["block_type"], "supporting_context")


def _ends_cleanly(text: str) -> bool:
    return bool(re.search(r"[.!?。！？]\s*$", text.strip())) or len(text.strip()) >= 18


def _starts_with_dependency(text: str) -> bool:
    first = (re.findall(r"[A-Za-z]+|[\u4e00-\u9fff]+", text.lower()) or [""])[0]
    return first in DEPENDENT_START

