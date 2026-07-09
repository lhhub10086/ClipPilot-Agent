from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def check_transcript_quality(
    *,
    segments: list[dict[str, Any]],
    video_duration: float,
    output_path: str,
    subtitle_path: str = "",
    backend: str = "",
) -> dict[str, Any]:
    report = build_quality_report(segments=segments, video_duration=video_duration, subtitle_path=subtitle_path, backend=backend)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "backend": "transcript_quality_gate",
        "output_path": str(path),
        "data": report,
    }


def build_quality_report(
    *,
    segments: list[dict[str, Any]],
    video_duration: float,
    subtitle_path: str = "",
    backend: str = "",
) -> dict[str, Any]:
    total = len(segments)
    texts = [str(item.get("text", "")).strip() for item in segments]
    non_empty = [text for text in texts if text]
    duration_coverage = _coverage_seconds(segments)
    coverage_ratio = duration_coverage / video_duration if video_duration > 0 else 0.0
    empty_segment_ratio = 1.0 - (len(non_empty) / total) if total else 1.0
    avg_segment_chars = sum(len(text) for text in non_empty) / len(non_empty) if non_empty else 0.0
    repetition_ratio = _repetition_ratio(non_empty)
    garbled_ratio = _garbled_ratio(non_empty)
    timestamp_monotonic = _timestamp_monotonic(segments)
    language = _detect_language(" ".join(non_empty))
    durations = [max(0.0, float(item.get("end", 0.0)) - float(item.get("start", 0.0))) for item in segments]
    avg_cue_duration = sum(durations) / len(durations) if durations else 0.0
    short_cue_ratio = sum(1 for item in durations if item < 3.0) / len(durations) if durations else 1.0
    long_cue_ratio = sum(1 for item in durations if item > 20.0) / len(durations) if durations else 0.0
    sentence_completeness_score = _sentence_completeness_score(non_empty)
    timing_precision = "coarse" if "refined" in backend or "asr" in backend else "sentence_level"

    issues: list[str] = []
    if total < 5:
        issues.append("too_few_segments")
    if coverage_ratio < 0.15:
        issues.append("low_duration_coverage")
    if empty_segment_ratio > 0.2:
        issues.append("too_many_empty_segments")
    if repetition_ratio > 0.35:
        issues.append("high_repetition")
    if garbled_ratio > 0.12:
        issues.append("garbled_text")
    if backend == "vtt_parser_asr_cache" and coverage_ratio < 0.2:
        issues.append("asr_cache_low_coverage")
    if not timestamp_monotonic:
        issues.append("non_monotonic_timestamps")
    if avg_segment_chars < 3:
        issues.append("segments_too_short")
    if short_cue_ratio > 0.5:
        issues.append("subtitle_segments_too_fragmented")

    score = 1.0
    score -= min(0.35, max(0.0, 0.45 - coverage_ratio) * 0.7)
    score -= min(0.25, empty_segment_ratio * 0.7)
    score -= min(0.25, repetition_ratio * 0.5)
    score -= min(0.55, garbled_ratio * 2.2)
    if not timestamp_monotonic:
        score -= 0.25
    if total < 5:
        score -= 0.25
    score -= min(0.2, max(0.0, short_cue_ratio - 0.25) * 0.35)
    score -= min(0.15, max(0.0, 0.45 - sentence_completeness_score) * 0.25)
    score = round(max(0.0, min(1.0, score)), 3)
    valid = score >= 0.6 and not {"garbled_text", "too_few_segments", "non_monotonic_timestamps", "asr_cache_low_coverage"} & set(issues)

    return {
        "transcript_valid": valid,
        "quality_score": score,
        "language_detected": language,
        "transcript_source": _source_from_backend(subtitle_path, backend),
        "asr_backend": backend if "asr" in backend or "whisper" in backend else "",
        "asr_fallback_used": backend == "vtt_parser_asr_cache",
        "coverage_ratio": round(coverage_ratio, 3),
        "raw_cue_count": total,
        "refined_cue_count": total if "refined" in backend else None,
        "avg_cue_duration": round(avg_cue_duration, 3),
        "short_cue_ratio": round(short_cue_ratio, 3),
        "long_cue_ratio": round(long_cue_ratio, 3),
        "timing_precision": timing_precision,
        "sentence_completeness_score": round(sentence_completeness_score, 3),
        "avg_segment_chars": round(avg_segment_chars, 3),
        "empty_segment_ratio": round(empty_segment_ratio, 3),
        "repetition_ratio": round(repetition_ratio, 3),
        "garbled_ratio": round(garbled_ratio, 3),
        "timestamp_monotonic": timestamp_monotonic,
        "duration_coverage_seconds": round(duration_coverage, 3),
        "segment_count": total,
        "major_issues": issues,
        "recommendation": _recommendation(valid, issues, backend),
    }


def _source_from_backend(subtitle_path: str, backend: str) -> str:
    if subtitle_path and backend == "vtt_parser":
        return "provided_vtt"
    if backend in {"faster_whisper", "vtt_parser_asr_cache"}:
        return "asr_generated"
    return "unknown"


def _recommendation(valid: bool, issues: list[str], backend: str) -> str:
    if valid:
        return "proceed"
    if "garbled_text" in issues and backend == "vtt_parser_asr_cache":
        return "rerun_asr"
    if "garbled_text" in issues:
        return "manual_subtitle_required"
    if "low_duration_coverage" in issues or "too_few_segments" in issues:
        return "use_vtt"
    if "subtitle_segments_too_fragmented" in issues:
        return "refine_subtitle"
    return "manual_subtitle_required"


def _coverage_seconds(segments: list[dict[str, Any]]) -> float:
    return sum(max(0.0, float(item.get("end", 0.0)) - float(item.get("start", 0.0))) for item in segments)


def _timestamp_monotonic(segments: list[dict[str, Any]]) -> bool:
    previous_end = -1.0
    for item in segments:
        start = float(item.get("start", 0.0))
        end = float(item.get("end", 0.0))
        if end < start or start < previous_end - 0.2:
            return False
        previous_end = max(previous_end, end)
    return True


def _repetition_ratio(texts: list[str]) -> float:
    if not texts:
        return 1.0
    normalized = [re.sub(r"\s+", " ", text.lower()).strip() for text in texts]
    counts = Counter(normalized)
    repeated = sum(count for text, count in counts.items() if text and count > 1)
    return repeated / len(texts)


def _garbled_ratio(texts: list[str]) -> float:
    text = " ".join(texts)
    if not text:
        return 1.0
    chars = [char for char in text if not char.isspace()]
    if not chars:
        return 1.0
    marker_count = len(re.findall(r"[\u9300-\u95ff\u7d00-\u7dff\u8b00-\u8bff]", text))
    replacement_count = text.count("�") + text.count("?")
    weird_bigram_count = len(re.findall(r"[\u9300-\u95ff][\u4e00-\u9fff]", text))
    return min(1.0, (marker_count + replacement_count * 3 + weird_bigram_count * 0.5) / len(chars))


def _detect_language(text: str) -> str:
    if not text:
        return "unknown"
    latin = len(re.findall(r"[A-Za-z]", text))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    if cjk > latin:
        return "zh_or_cjk"
    if latin > 0:
        return "en_or_latin"
    return "unknown"


def _sentence_completeness_score(texts: list[str]) -> float:
    if not texts:
        return 0.0
    complete = 0
    for text in texts:
        stripped = text.strip()
        if re.search(r"[銆傦紒锛?!?]\s*$", stripped) or len(stripped) >= 18:
            complete += 1
    return complete / len(texts)

