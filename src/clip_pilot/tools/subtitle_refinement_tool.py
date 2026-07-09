from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

from clip_pilot.agent.subtitle_quality_judge import judge_subtitle_quality
from clip_pilot.agent.subtitle_refiner import build_semantic_blocks_with_llm, refine_cues_with_llm

DEFAULT_GLOSSARY = [
    "初中物理",
    "高中物理",
    "区别和联系",
    "物理知识",
    "加速度",
    "速度",
    "位移",
    "受力分析",
    "牛顿运动定律",
    "运动学",
    "标量",
    "矢量",
    "例题",
    "易错点",
]

TRADITIONAL_MAP = str.maketrans(
    {
        "為": "为",
        "聯": "联",
        "繫": "系",
        "題": "题",
        "們": "们",
        "農": "农",
        "識": "识",
        "講": "讲",
        "給": "给",
        "進": "进",
        "後": "后",
        "沒": "没",
        "義": "义",
        "因": "因",
    }
)

CORRECTIONS = [
    ("一进二后", "一节课"),
    ("一进二侯", "一节课"),
    ("讲没有意义", "讲这些没有意义"),
    ("高农物理", "高中物理"),
    ("初农物理", "初中物理"),
    ("信奥义", "新高一"),
]

SHORT_FILLER_RE = re.compile(r"^(那么|好|对不对|是不是|第一个|第二个|第三个|还有呢|嗯|啊|吧|吗)[，。！？!?]*$")
END_RE = re.compile("[\\u3002\\uff01\\uff1f.!?]\\s*$")


def refine_subtitle_file(
    raw_subtitle_path: str,
    output_dir: str,
    *,
    domain_glossary: list[str] | None = None,
    language: str = "zh",
    config: dict[str, Any] | None = None,
    use_llm: bool = False,
) -> dict[str, Any]:
    from .subtitle_tool import parse_subtitle

    parsed = parse_subtitle(raw_subtitle_path)
    if not parsed.get("success"):
        return parsed
    raw_segments = parsed["data"]["segments"]
    return refine_segments(raw_segments, output_dir, domain_glossary=domain_glossary, language=language, raw_subtitle_path=raw_subtitle_path, config=config, use_llm=use_llm)


def refine_segments(
    raw_segments: list[dict[str, Any]],
    output_dir: str,
    *,
    domain_glossary: list[str] | None = None,
    language: str = "zh",
    raw_subtitle_path: str = "",
    config: dict[str, Any] | None = None,
    use_llm: bool = False,
) -> dict[str, Any]:
    glossary = domain_glossary or DEFAULT_GLOSSARY
    cleaned = []
    corrections: list[dict[str, str]] = []
    raw_cues = []
    for idx, item in enumerate(raw_segments, start=1):
        text, applied = clean_text(str(item.get("text", "")))
        corrections.extend(applied)
        if text:
            cue = {"cue_id": f"cue_{idx:04}", "start": float(item["start"]), "end": float(item["end"]), "raw_text": text, "text": text}
            cleaned.append(cue)
            raw_cues.append(cue)

    if use_llm and config:
        refiner_result = refine_cues_with_llm(raw_cues=raw_cues, output_dir=output_dir, config=config, domain_glossary=glossary)
        sentence_units = refiner_result["data"]["sentence_units"]
        refinement_backend = refiner_result["backend"]
        llm_called = bool(refiner_result["data"].get("llm_called"))
        llm_repair_rounds = 0
        unresolved_items = refiner_result["data"].get("unresolved_items", [])
    else:
        sentence_units = build_rule_sentence_units(cleaned)
        refinement_backend = "rule_fallback"
        llm_called = False
        llm_repair_rounds = 0
        unresolved_items = []

    block_result = build_semantic_blocks_with_llm(sentence_units=sentence_units, output_dir=output_dir, config=config or {}, domain_glossary=glossary)
    semantic_blocks = block_result["data"]["semantic_blocks"]
    if use_llm and config:
        judge_result = judge_subtitle_quality(
            raw_cues=raw_cues,
            sentence_units=sentence_units,
            semantic_blocks=semantic_blocks,
            domain_glossary=glossary,
            output_dir=output_dir,
            config=config,
        )
        subtitle_judge = judge_result["data"]["judge_response"]
    else:
        subtitle_judge = {"passed": True, "score": 0.0, "problems": [], "backend": "not_run"}

    refined = [{"start": unit["start"], "end": unit["end"], "text": unit["refined_text"]} for unit in sentence_units]

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    srt_path = root / "refined_subtitle.srt"
    vtt_path = root / "refined_subtitle.vtt"
    txt_path = root / "refined_subtitle.txt"
    report_path = root / "subtitle_refinement_report.json"
    sentence_units_path = root / "sentence_units.json"
    semantic_blocks_path = root / "semantic_blocks.json"

    write_srt(refined, srt_path)
    vtt_path.write_text(to_vtt(refined), encoding="utf-8")
    txt_path.write_text("\n".join(f"[{item['start']:8.3f} - {item['end']:8.3f}] {item['text']}" for item in refined), encoding="utf-8")
    sentence_units_path.write_text(json.dumps({"sentence_units": sentence_units}, ensure_ascii=False, indent=2), encoding="utf-8")
    semantic_blocks_path.write_text(json.dumps({"semantic_blocks": semantic_blocks}, ensure_ascii=False, indent=2), encoding="utf-8")

    raw_durations = [float(item["end"]) - float(item["start"]) for item in raw_segments]
    refined_durations = [float(item["end"]) - float(item["start"]) for item in refined]
    multi_thought_ratio = _multi_thought_ratio(sentence_units)
    completeness_score = sum(1 for unit in sentence_units if unit.get("sentence_complete")) / len(sentence_units) if sentence_units else 0.0
    unresolved_count = len(unresolved_items)
    report = {
        "raw_subtitle_path": raw_subtitle_path,
        "raw_cue_count": len(raw_segments),
        "refined_cue_count": len(refined),
        "sentence_unit_count": len(sentence_units),
        "semantic_block_count": len(semantic_blocks),
        "merge_count": max(0, len(cleaned) - len(refined)),
        "split_count": max(0, len(refined) - len(cleaned)),
        "traditional_to_simplified": True,
        "keyword_corrections": corrections[:80],
        "domain_glossary": glossary,
        "avg_raw_cue_duration": round(sum(raw_durations) / len(raw_durations), 3) if raw_durations else 0.0,
        "avg_refined_cue_duration": round(sum(refined_durations) / len(refined_durations), 3) if refined_durations else 0.0,
        "avg_sentence_duration": round(sum(refined_durations) / len(refined_durations), 3) if refined_durations else 0.0,
        "p50_sentence_duration": round(statistics.median(refined_durations), 3) if refined_durations else 0.0,
        "p90_sentence_duration": round(_percentile(refined_durations, 0.9), 3) if refined_durations else 0.0,
        "sentence_under_3s_ratio": round(sum(1 for item in refined_durations if item < 3.0) / len(refined_durations), 3) if refined_durations else 1.0,
        "sentence_over_15s_ratio": round(sum(1 for item in refined_durations if item > 15.0) / len(refined_durations), 3) if refined_durations else 0.0,
        "multi_thought_sentence_ratio": round(multi_thought_ratio, 3),
        "sentence_completeness_score": round(completeness_score, 3),
        "unresolved_asr_error_count": unresolved_count,
        "correction_count": len(corrections),
        "low_confidence_correction_count": _low_confidence_count(sentence_units),
        "subtitle_judge_score": subtitle_judge.get("score"),
        "subtitle_judge_passed": subtitle_judge.get("passed"),
        "refinement_backend": refinement_backend,
        "llm_called": llm_called,
        "llm_repair_rounds": llm_repair_rounds,
        "short_cue_ratio": round(sum(1 for item in refined_durations if item < 3.0) / len(refined_durations), 3) if refined_durations else 1.0,
        "long_cue_ratio": round(sum(1 for item in refined_durations if item > 20.0) / len(refined_durations), 3) if refined_durations else 0.0,
        "timing_precision": "coarse",
        "timing_source_distribution": {"raw_asr_cue_boundaries": len(sentence_units)},
        "language": language,
        "unresolved_items": unresolved_items[:80],
        "recommendation": recommendation(refined, refined_durations, subtitle_judge=subtitle_judge, multi_thought_ratio=multi_thought_ratio, unresolved_count=unresolved_count),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "backend": "subtitle_refinement",
        "output_path": str(vtt_path),
        "data": {
            "segments": refined,
            "segment_count": len(refined),
            "srt_path": str(srt_path),
            "vtt_path": str(vtt_path),
            "txt_path": str(txt_path),
            "report_path": str(report_path),
            "sentence_units_path": str(sentence_units_path),
            "semantic_blocks_path": str(semantic_blocks_path),
            "sentence_units": sentence_units,
            "semantic_blocks": semantic_blocks,
            "report": report,
        },
    }


def clean_text(text: str) -> tuple[str, list[dict[str, str]]]:
    original = text
    text = text.translate(TRADITIONAL_MAP)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[,，]+", "，", text)
    text = re.sub(r"[.。]+", "。", text)
    applied = []
    for wrong, right in CORRECTIONS:
        if wrong in text:
            text = text.replace(wrong, right)
            applied.append({"from": wrong, "to": right})
    if text and not END_RE.search(text) and len(text) > 14:
        text += "。"
    if original != text and not applied:
        applied.append({"from": "traditional_or_spacing", "to": "normalized"})
    return text.strip(" 锛?"), applied


def build_rule_sentence_units(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refined = merge_short_cues(segments)
    refined = split_long_cues(refined)
    units = []
    for idx, item in enumerate(refined, start=1):
        cue_ids = item.get("source_cue_ids") or [item.get("cue_id", f"cue_{idx:04}")]
        units.append(
            {
                "sentence_id": f"sentence_{idx:04}",
                "start": item["start"],
                "end": item["end"],
                "duration": round(float(item["end"]) - float(item["start"]), 3),
                "refined_text": item["text"],
                "text": item["text"],
                "original_text": item.get("original_text", item["text"]),
                "source_cue_ids": cue_ids,
                "corrections": [],
                "correction_confidence": None,
                "sentence_complete": bool(END_RE.search(item["text"]) or len(item["text"]) >= 12),
                "timing_source": "raw_asr_cue_boundaries",
            }
        )
    return units


def merge_short_cues(segments: list[dict[str, Any]], min_duration: float = 4.0, max_duration: float = 12.0, hard_max: float = 12.0) -> list[dict[str, Any]]:
    refined: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for segment in segments:
        if not current:
            current = [segment]
            continue
        gap = float(segment["start"]) - float(current[-1]["end"])
        duration_with_next = float(segment["end"]) - float(current[0]["start"])
        current_text = "".join(str(item["text"]) for item in current)
        should_merge = gap < 1.0
        should_merge = should_merge or not END_RE.search(current_text)
        should_merge = should_merge or _is_short_oral_fragment(current_text)
        should_merge = should_merge or (float(current[-1]["end"]) - float(current[0]["start"]) < min_duration)
        if should_merge and duration_with_next <= hard_max:
            current.append(segment)
        else:
            refined.append(_merge_group(current))
            current = [segment]
    if current:
        refined.append(_merge_group(current))

    second_pass: list[dict[str, Any]] = []
    for item in refined:
        if second_pass:
            prev = second_pass[-1]
            gap = float(item["start"]) - float(prev["end"])
            merged_duration = float(item["end"]) - float(prev["start"])
            if (float(prev["end"]) - float(prev["start"]) < min_duration or _is_short_oral_fragment(prev["text"])) and gap < 1.0 and merged_duration <= hard_max:
                second_pass[-1] = _merge_group([prev, item])
                continue
        second_pass.append(item)
    return second_pass


def split_long_cues(segments: list[dict[str, Any]], hard_max: float = 20.0) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in segments:
        duration = float(item["end"]) - float(item["start"])
        if duration <= hard_max:
            output.append(item)
            continue
        parts = split_text_sentences(str(item["text"]))
        if len(parts) <= 1:
            output.append(item)
            continue
        total_chars = sum(len(part) for part in parts) or 1
        cursor = float(item["start"])
        for part in parts:
            part_duration = duration * len(part) / total_chars
            end = cursor + part_duration
            output.append({"start": round(cursor, 3), "end": round(end, 3), "text": part})
            cursor = end
    return output


def split_text_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[銆傦紒锛??])", text)
    return [part.strip() for part in parts if part.strip()]


def _merge_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    text = "".join(str(item["text"]).strip() for item in group)
    text = re.sub(r"([銆傦紒锛??])([銆傦紒锛??])+", r"\1", text)
    cue_ids = []
    original = []
    for item in group:
        cue_ids.extend(item.get("source_cue_ids") or [item.get("cue_id", "")])
        original.append(str(item.get("raw_text") or item.get("original_text") or item.get("text") or ""))
    return {"start": round(float(group[0]["start"]), 3), "end": round(float(group[-1]["end"]), 3), "text": text, "source_cue_ids": [cue_id for cue_id in cue_ids if cue_id], "original_text": "".join(original)}


def _is_short_oral_fragment(text: str) -> bool:
    cleaned = re.sub(r"[锛?銆?!?锛焅s]", "", text)
    return len(cleaned) <= 8 or bool(SHORT_FILLER_RE.match(text.strip()))


def write_srt(segments: list[dict[str, Any]], path: Path) -> None:
    lines = []
    for idx, item in enumerate(segments, start=1):
        lines.append(str(idx))
        lines.append(f"{format_time(float(item['start'])).replace('.', ',')} --> {format_time(float(item['end'])).replace('.', ',')}")
        lines.append(str(item["text"]))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def to_vtt(segments: list[dict[str, Any]]) -> str:
    lines = ["WEBVTT", ""]
    for idx, item in enumerate(segments, start=1):
        lines.append(str(idx))
        lines.append(f"{format_time(float(item['start']))} --> {format_time(float(item['end']))}")
        lines.append(str(item["text"]))
        lines.append("")
    return "\n".join(lines)


def format_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    rest = seconds - hours * 3600 - minutes * 60
    return f"{hours:02}:{minutes:02}:{rest:06.3f}"


def recommendation(segments: list[dict[str, Any]], durations: list[float], *, subtitle_judge: dict[str, Any] | None = None, multi_thought_ratio: float = 0.0, unresolved_count: int = 0) -> str:
    if not segments:
        return "needs_better_asr"
    short_ratio = sum(1 for item in durations if item < 3.0) / len(durations)
    long_ratio = sum(1 for item in durations if item > 20.0) / len(durations)
    over_15 = sum(1 for item in durations if item > 15.0) / len(durations)
    avg_chars = sum(len(str(item["text"])) for item in segments) / len(segments)
    if short_ratio > 0.5 or avg_chars < 8:
        return "needs_better_asr"
    if long_ratio > 0.2 or over_15 >= 0.1 or multi_thought_ratio >= 0.1:
        return "needs_manual_subtitle"
    if subtitle_judge and subtitle_judge.get("score") is not None and float(subtitle_judge.get("score", 0.0)) < 0.75:
        return "needs_manual_subtitle"
    if unresolved_count > max(10, len(segments) * 0.1):
        return "needs_manual_subtitle"
    return "usable_for_review"


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[idx]


def _multi_thought_ratio(sentence_units: list[dict[str, Any]]) -> float:
    if not sentence_units:
        return 1.0
    return sum(1 for unit in sentence_units if _multi_thought(unit.get("refined_text", ""))) / len(sentence_units)


def _multi_thought(text: str) -> bool:
    markers = ["第一个", "第二个", "第三个", "首先", "然后", "接下来", "最后"]
    return sum(1 for marker in markers if marker in text) >= 2


def _low_confidence_count(sentence_units: list[dict[str, Any]]) -> int:
    count = 0
    for unit in sentence_units:
        for correction in unit.get("corrections", []):
            if isinstance(correction, dict) and float(correction.get("confidence", 1.0) or 0.0) < 0.6:
                count += 1
    return count

