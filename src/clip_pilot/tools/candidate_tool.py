from __future__ import annotations

import math
import re
from typing import Any

from .subtitle_tool import transcript_text


DEFINITION_WORDS = {"define", "definition", "means", "refers", "called", "concept", "idea"}
METHOD_WORDS = {"formula", "equation", "function", "objective", "optimize", "minimize", "maximize", "algorithm", "step", "procedure", "method", "gradient", "model"}
EXAMPLE_WORDS = {"example", "instance", "suppose", "case", "demo", "application"}
SUMMARY_WORDS = {"therefore", "summary", "remember", "important", "key", "finally", "conclusion"}
QUESTION_WORDS = {"why", "how", "what", "when", "where"}
AVOID_WORDS = {"welcome", "housekeeping", "subscribe", "thanks", "agenda", "introduction"}
CHINESE_KEYWORDS = {
    "问题",
    "区别",
    "联系",
    "学习",
    "概念",
    "定义",
    "方法",
    "例子",
    "重要",
    "关键",
    "总结",
    "公式",
    "步骤",
    "原理",
    "物理",
    "知识",
    "理解",
}
CHINESE_AVOID = {"欢迎", "订阅", "谢谢", "下次", "开场"}


def generate_candidates(segments: list[dict[str, Any]], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or {}
    task_type = policy.get("task_type", "general")
    duration = max([float(item["end"]) for item in segments], default=0.0)
    duration_policy = policy.get("duration_policy", {})
    min_dur = float(duration_policy.get("min_segment_seconds", 20))
    max_dur = float(duration_policy.get("max_segment_seconds", 90))
    if task_type == "highlight_reel":
        windows = [6.0, 8.0, 10.0, 12.0, 15.0, 18.0]
        step = 3.0
        min_tokens = 5
    else:
        windows = sorted({max(min_dur, 20.0), min(45.0, max_dur), min(60.0, max_dur)})
        step = 10.0
        min_tokens = 12

    candidates = []
    idx = 1
    for window in windows:
        if window < min_dur - 0.01 or window > max_dur + 0.01:
            continue
        cursor = 0.0
        while cursor < max(duration - 1.0, 0.0):
            end = min(duration, cursor + window)
            if end - cursor < min_dur - 0.01:
                cursor += step
                continue
            text = transcript_text(segments, cursor, end)
            token_count = len(tokenize(text))
            if token_count >= min_tokens:
                features = score_text(text, cursor, duration, end - cursor, task_type)
                candidates.append(
                    {
                        "candidate_id": f"cand_{idx:04}",
                        "start": round(cursor, 3),
                        "end": round(end, 3),
                        "duration": round(end - cursor, 3),
                        "transcript": text,
                        "transcript_token_count": token_count,
                        "semantic_boundary_score": features["semantic_boundary_score"],
                        "density_score": features["density_score"],
                        "keyword_score": features["keyword_score"],
                        "cut_quality_score": features["cut_quality_score"],
                        "score": features["cut_quality_score"],
                        "original_start": round(cursor, 3),
                        "original_end": round(end, 3),
                        "refined_start": round(cursor, 3),
                        "refined_end": round(end, 3),
                        "boundary_refined": False,
                    }
                )
                idx += 1
            cursor += step
    return {"success": True, "backend": "subtitle_candidate_generator", "data": {"candidate_count": len(candidates), "candidates": candidates}}


def select_candidates(candidates: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    task_type = policy.get("task_type", "general")
    segment_policy = policy.get("segment_count_policy", {})
    duration_policy = policy.get("duration_policy", {})
    selection_policy = policy.get("selection_policy", {})
    max_segments = int(segment_policy.get("max_segments") or 5)
    target_segments = segment_policy.get("target_segments")
    target_segments = int(target_segments) if target_segments else None
    limit = min(max_segments, target_segments) if target_segments else max_segments
    max_final_duration = float(duration_policy.get("max_final_duration_seconds") or 180)
    min_quality = float(selection_policy.get("min_cut_quality_score") or 0.6)
    max_overlap = 2.0 if task_type == "highlight_reel" else 0.05
    max_duplicate = 0.25 if task_type == "highlight_reel" else 0.5

    selected = []
    used_duration = 0.0
    ranked = sorted(candidates, key=lambda value: rank_score(value, task_type), reverse=True)
    for item in ranked:
        if len(selected) >= limit:
            break
        if float(item["cut_quality_score"]) < min_quality:
            continue
        if used_duration + float(item["duration"]) > max_final_duration:
            continue
        if any(overlap_seconds(item, old) > max_overlap for old in selected):
            continue
        duplicate = max([text_duplicate_ratio(item, old) for old in selected], default=0.0)
        if duplicate > max_duplicate:
            continue
        item = dict(item)
        item["clip_id"] = f"clip_{len(selected)+1:03}"
        item["duplicate_ratio"] = round(duplicate, 4)
        item["selection_reason"] = (
            f"Selected by adaptive policy: quality={item['cut_quality_score']:.2f}, "
            f"duration={item['duration']:.1f}s, duplicate_ratio={duplicate:.2f}, within final duration budget."
        )
        selected.append(item)
        used_duration += float(item["duration"])
    return {
        "success": True,
        "backend": "policy_candidate_selector",
        "data": {
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "selected": selected,
            "used_duration": round(used_duration, 3),
            "min_cut_quality_score": min_quality,
        },
    }


def score_text(text: str, start: float, video_duration: float, candidate_duration: float, task_type: str) -> dict[str, float]:
    words = tokenize(text)
    if not words:
        return {"keyword_score": 0.0, "density_score": 0.0, "semantic_boundary_score": 0.0, "cut_quality_score": 0.0}
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    chinese_keyword_hits = sum(1 for phrase in CHINESE_KEYWORDS if phrase in text)
    keyword_hits = count_hits(words, DEFINITION_WORDS | METHOD_WORDS | EXAMPLE_WORDS | SUMMARY_WORDS | QUESTION_WORDS) + chinese_keyword_hits
    avoid_hits = count_hits(words, AVOID_WORDS) + sum(1 for phrase in CHINESE_AVOID if phrase in text)
    keyword_score = min(keyword_hits / 4.0, 1.0)
    info_units = len(words) + len(chinese_chars) / 2.0
    density_score = min(info_units / max(candidate_duration * 2.2, 1.0), 1.0)
    semantic_boundary_score = boundary_score(text)
    position_penalty = 0.12 if start / max(video_duration, 1.0) < 0.04 and avoid_hits else 0.0
    if task_type == "highlight_reel":
        duration_pref = 1.0 - min(abs(candidate_duration - 10.0) / 12.0, 1.0)
        quality = 0.32 * density_score + 0.30 * keyword_score + 0.23 * semantic_boundary_score + 0.15 * duration_pref - position_penalty
    else:
        quality = 0.45 * keyword_score + 0.35 * density_score + 0.20 * semantic_boundary_score - position_penalty
    if chinese_chars:
        quality += 0.04
    return {
        "keyword_score": round(keyword_score, 4),
        "density_score": round(density_score, 4),
        "semantic_boundary_score": round(semantic_boundary_score, 4),
        "cut_quality_score": round(max(0.0, min(1.0, quality)), 4),
    }


def rank_score(item: dict[str, Any], task_type: str) -> float:
    score = float(item.get("cut_quality_score", 0.0))
    if task_type == "highlight_reel":
        duration = float(item.get("duration", 0.0))
        if 8.0 <= duration <= 15.0:
            score += 0.04
        score += 0.02 * float(item.get("semantic_boundary_score", 0.0))
    return score


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z\-']+|[\u4e00-\u9fff]+", text.lower())


def count_hits(words: list[str], keywords: set[str]) -> int:
    return sum(1 for word in words if word in keywords)


def boundary_score(text: str) -> float:
    stripped = text.strip()
    if not stripped:
        return 0.0
    score = 0.55
    if stripped[-1:] in {".", "?", "!", "。", "？", "！"}:
        score += 0.25
    if len(stripped.split()) >= 8:
        score += 0.10
    if re.search(r"\b(first|second|third|finally|therefore|because|so|now)\b", stripped.lower()):
        score += 0.10
    return round(min(score, 1.0), 4)


def iou(a: dict[str, Any], b: dict[str, Any]) -> float:
    left = max(float(a["start"]), float(b["start"]))
    right = min(float(a["end"]), float(b["end"]))
    inter = max(0.0, right - left)
    union = max(float(a["end"]), float(b["end"])) - min(float(a["start"]), float(b["start"]))
    return inter / union if union > 0 else 0.0


def overlap_seconds(a: dict[str, Any], b: dict[str, Any]) -> float:
    return max(0.0, min(float(a["end"]), float(b["end"])) - max(float(a["start"]), float(b["start"])))


def text_duplicate_ratio(a: dict[str, Any], b: dict[str, Any]) -> float:
    aw = set(tokenize(str(a.get("transcript", ""))))
    bw = set(tokenize(str(b.get("transcript", ""))))
    if not aw or not bw:
        return 0.0
    return len(aw & bw) / max(1, min(len(aw), len(bw)))

