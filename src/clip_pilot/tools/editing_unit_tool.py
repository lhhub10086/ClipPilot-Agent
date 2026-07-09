from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_editing_units(
    *,
    sentence_units_path: str,
    semantic_blocks_path: str,
    output_path: str,
    min_duration: float = 8.0,
    max_duration: float = 25.0,
    asr_risk_report_path: str | None = None,
) -> dict[str, Any]:
    units = json.loads(Path(sentence_units_path).read_text(encoding="utf-8")).get("sentence_units", [])
    blocks = json.loads(Path(semantic_blocks_path).read_text(encoding="utf-8")).get("semantic_blocks", [])
    risk_by_sentence = _load_risk_by_sentence(asr_risk_report_path)
    unit_map = {unit["sentence_id"]: unit for unit in units}
    editing_units: list[dict[str, Any]] = []

    for block in blocks:
        current: list[dict[str, Any]] = []
        for sid in block.get("sentence_ids", []):
            if sid not in unit_map:
                continue
            unit = unit_map[sid]
            if current and float(unit["end"]) - float(current[0]["start"]) > max_duration:
                editing_units.append(_make_unit(len(editing_units) + 1, current, block, risk_by_sentence))
                current = []
            current.append(unit)
            duration = float(current[-1]["end"]) - float(current[0]["start"])
            if duration >= min_duration:
                editing_units.append(_make_unit(len(editing_units) + 1, current, block, risk_by_sentence))
                current = []
        if current:
            editing_units.append(_make_unit(len(editing_units) + 1, current, block, risk_by_sentence))

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"editing_units": editing_units}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "backend": "editing_unit_builder",
        "output_path": str(path),
        "data": {"editing_units": editing_units, "editing_unit_count": len(editing_units)},
    }


def annotate_semantic_blocks_with_risk(
    *,
    semantic_blocks_path: str,
    asr_risk_report_path: str,
    output_path: str,
) -> dict[str, Any]:
    blocks = json.loads(Path(semantic_blocks_path).read_text(encoding="utf-8")).get("semantic_blocks", [])
    risk_by_sentence = _load_risk_by_sentence(asr_risk_report_path)
    annotated = [annotate_block(block, risk_by_sentence) for block in blocks]
    _attach_safe_alternatives(annotated)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"semantic_blocks": annotated}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "backend": "semantic_block_risk_annotator",
        "output_path": str(path),
        "data": {"semantic_blocks": annotated, "block_count": len(annotated)},
    }


def _attach_safe_alternatives(blocks: list[dict[str, Any]]) -> None:
    for block in blocks:
        if block.get("lexical_risk_level") == "low_risk":
            block["safe_alternative_ids"] = []
            continue
        topic = block.get("topic")
        alternatives = [
            other.get("block_id")
            for other in blocks
            if other is not block
            and other.get("lexical_risk_level") == "low_risk"
            and (other.get("topic") == topic or _topic_overlap(block, other))
        ]
        block["safe_alternative_ids"] = [str(item) for item in alternatives[:5] if item]


def _topic_overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    a_text = str(a.get("text", ""))
    b_text = str(b.get("text", ""))
    terms = ["初中物理", "高中物理", "力", "电", "浮力", "加速度", "学习方法", "运动学"]
    return any(term in a_text and term in b_text for term in terms)


def annotate_block(block: dict[str, Any], risk_by_sentence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sentence_ids = [str(sid) for sid in block.get("sentence_ids", [])]
    unresolved = [sid for sid in sentence_ids if sid in risk_by_sentence]
    lexical_risk_score = max([float(risk_by_sentence[sid].get("risk_score", 0.0)) for sid in unresolved] or [0.0])
    risk_level = _risk_level(lexical_risk_score)
    out = dict(block)
    out["contains_unresolved_asr"] = bool(unresolved)
    out["unresolved_sentence_ids"] = unresolved
    out["lexical_risk_score"] = round(lexical_risk_score, 3)
    out["lexical_risk_level"] = risk_level
    out["narrative_importance"] = _narrative_importance(out)
    out["bridge_importance"] = _bridge_importance(out)
    out["safe_alternative_ids"] = []
    out["required_for_coherence"] = False
    out["review_if_selected"] = risk_level in {"medium_risk", "high_risk"}
    out["safe_for_auto_edit"] = risk_level == "low_risk"
    out["requires_manual_review"] = risk_level in {"medium_risk", "high_risk"}
    return out


def _make_unit(
    idx: int,
    sentence_units: list[dict[str, Any]],
    block: dict[str, Any],
    risk_by_sentence: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    risk_by_sentence = risk_by_sentence or {}
    text = "".join(str(unit.get("refined_text") or unit.get("text") or "") for unit in sentence_units)
    unresolved_sentence_ids = [unit["sentence_id"] for unit in sentence_units if unit["sentence_id"] in risk_by_sentence]
    lexical_risk_score = max([float(risk_by_sentence[sid].get("risk_score", 0.0)) for sid in unresolved_sentence_ids] or [0.0])
    risk_level = _risk_level(lexical_risk_score)
    out = {
        "editing_unit_id": f"editing_unit_{idx:04}",
        "sentence_ids": [unit["sentence_id"] for unit in sentence_units],
        "start": sentence_units[0]["start"],
        "end": sentence_units[-1]["end"],
        "duration": round(float(sentence_units[-1]["end"]) - float(sentence_units[0]["start"]), 3),
        "topic": block.get("topic", "course_content"),
        "text": text,
        "semantic_complete": bool(len(text) >= 12 and sentence_units[-1].get("sentence_complete", True)),
        "unresolved_sentence_ids": unresolved_sentence_ids,
        "contains_unresolved_asr": bool(unresolved_sentence_ids),
        "lexical_risk_score": round(lexical_risk_score, 3),
        "lexical_risk_level": risk_level,
        "safe_for_auto_edit": risk_level == "low_risk",
        "requires_manual_review": risk_level in {"medium_risk", "high_risk"},
        "review_if_selected": risk_level in {"medium_risk", "high_risk"},
        "narrative_importance": 0.0,
        "bridge_importance": 0.0,
        "safe_alternative_ids": [],
        "required_for_coherence": False,
    }
    out["narrative_importance"] = _narrative_importance(out)
    out["bridge_importance"] = _bridge_importance(out)
    return out


def _risk_level(score: float) -> str:
    if score >= 0.85:
        return "high_risk"
    if score >= 0.55:
        return "medium_risk"
    return "low_risk"


def _narrative_importance(item: dict[str, Any]) -> float:
    text = str(item.get("text", ""))
    score = 0.2
    for term in ["初中物理", "高中物理", "区别", "联系", "加速度", "受力分析", "牛顿", "核心", "重点", "方法", "公式"]:
        if term in text:
            score += 0.08
    if item.get("block_type") in {"definition", "explanation", "conclusion", "introduction"}:
        score += 0.12
    if 8 <= float(item.get("duration", 0.0) or 0.0) <= 45:
        score += 0.1
    return round(min(1.0, score), 3)


def _bridge_importance(item: dict[str, Any]) -> float:
    text = str(item.get("text", ""))
    score = 0.0
    for marker in ["首先", "那么", "所以", "接下来", "第二", "第三", "最后", "总结", "区别", "联系"]:
        if marker in text:
            score += 0.12
    if item.get("block_type") in {"introduction", "transition", "conclusion"}:
        score += 0.2
    return round(min(1.0, score), 3)


def _load_risk_by_sentence(path: str | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    risk_path = Path(path)
    if not risk_path.exists():
        return {}
    payload = json.loads(risk_path.read_text(encoding="utf-8"))
    return {str(item.get("sentence_id")): item for item in payload.get("risks", []) if item.get("sentence_id")}

