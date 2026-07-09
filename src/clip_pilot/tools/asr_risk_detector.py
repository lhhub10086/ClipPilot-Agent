from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_SUSPECT_TERMS = {
    "信奥义",
    "牙肠",
    "福利",
    "刑法",
    "护理教师",
    "高农",
    "初农",
}

PHYSICS_TERMS = {
    "初中物理",
    "高中物理",
    "加速度",
    "速度",
    "位移",
    "受力分析",
    "牛顿",
    "运动学",
    "力学",
    "电学",
    "浮力",
    "压强",
    "密度",
    "质量",
    "标量",
    "矢量",
    "例题",
}


def detect_asr_risks(
    *,
    sentence_units_path: str,
    semantic_blocks_path: str,
    output_path: str,
    glossary: list[str] | None = None,
    threshold: float = 0.55,
) -> dict[str, Any]:
    units = json.loads(Path(sentence_units_path).read_text(encoding="utf-8")).get("sentence_units", [])
    blocks = json.loads(Path(semantic_blocks_path).read_text(encoding="utf-8")).get("semantic_blocks", [])
    report = build_risk_report(units, blocks, glossary=glossary, threshold=threshold)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "asr_risk_detector", "output_path": str(path), "data": report}


def build_risk_report(sentence_units: list[dict[str, Any]], semantic_blocks: list[dict[str, Any]], glossary: list[str] | None = None, threshold: float = 0.55) -> dict[str, Any]:
    glossary_terms = set(glossary or []) | PHYSICS_TERMS
    unresolved_by_id = _unresolved_by_sentence(sentence_units)
    risks = []
    for unit in sentence_units:
        text = str(unit.get("refined_text") or unit.get("text") or "")
        risk_types: list[str] = []
        score = 0.0
        suspect_hits = sorted(term for term in DEFAULT_SUSPECT_TERMS if term in text)
        if suspect_hits:
            risk_types.append("semantic_anomaly")
            risk_types.append("suspected_homophone")
            score += 0.45 + min(0.2, 0.05 * len(suspect_hits))
        if _garbled(text):
            risk_types.append("garbled_text")
            score += 0.35
        if _low_domain_relevance(text, glossary_terms):
            risk_types.append("low_domain_relevance")
            score += 0.15
        if unit.get("sentence_id") in unresolved_by_id:
            risk_types.append("context_inconsistency")
            score += 0.35
        if _grammar_anomaly(text):
            risk_types.append("semantic_anomaly")
            score += 0.2
        score = round(min(1.0, score), 3)
        if score >= threshold:
            risks.append(
                {
                    "sentence_id": unit.get("sentence_id"),
                    "start": unit.get("start"),
                    "end": unit.get("end"),
                    "text": text,
                    "risk_types": sorted(set(risk_types)),
                    "risk_score": score,
                    "requires_re_asr": score >= threshold,
                    "source_cue_ids": unit.get("source_cue_ids", []),
                }
            )
    risks.sort(key=lambda item: (-float(item["risk_score"]), float(item["start"] or 0.0)))
    return {
        "risk_sentence_count": len(risks),
        "threshold": threshold,
        "risks": risks,
        "semantic_block_count": len(semantic_blocks),
    }


def _unresolved_by_sentence(sentence_units: list[dict[str, Any]]) -> set[str]:
    out = set()
    for unit in sentence_units:
        text = str(unit.get("refined_text", ""))
        if any(term in text for term in DEFAULT_SUSPECT_TERMS):
            out.add(str(unit.get("sentence_id")))
    return out


def _garbled(text: str) -> bool:
    return bool(re.search(r"[閿燂拷]{1,}|[A-Za-z]{12,}", text))


def _low_domain_relevance(text: str, glossary: set[str]) -> bool:
    if len(text) < 8:
        return False
    return not any(term in text for term in glossary) and any(term in text for term in ["鏁欏笀", "鍒戞硶", "鎶ょ悊", "娌捐彍", "鐗欒偁"])


def _grammar_anomaly(text: str) -> bool:
    return bool(re.search(r"(浠€涔堝彨鐗檤楂樹腑鐗╃悊瀛︽牎|淇″湪浠€涔堝湴鏂箌鏁伴噺涔嬪悗)", text))

