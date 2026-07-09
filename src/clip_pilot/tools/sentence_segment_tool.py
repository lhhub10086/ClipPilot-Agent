from __future__ import annotations

import re
from typing import Any


END_RE = re.compile("[\\u3002\\uff01\\uff1f.!?\\uff1b;]\\s*$")
SOFT_END_RE = re.compile("[\\uff0c,\\u3001\\uff1a:]\\s*$")
DEPENDENT_START_RE = re.compile(
    "^\\s*(\\u7136\\u540e|\\u6240\\u4ee5|\\u4f46\\u662f|\\u800c\\u4e14|\\u56e0\\u4e3a|\\u90a3\\u4e48|\\u8fd9\\u4e2a|\\u90a3\\u4e2a|\\u5b83|\\u8fd9|\\u90a3|and|but|so|because)\\b",
    re.IGNORECASE,
)


def build_sentences(cues: list[dict[str, Any]], max_gap: float = 1.2, max_duration: float = 24.0) -> dict[str, Any]:
    sentences: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for cue in cues:
        if current:
            gap = float(cue["start"]) - float(current[-1]["end"])
            duration = float(cue["end"]) - float(current[0]["start"])
            current_text = " ".join(str(item["text"]).strip() for item in current).strip()
            next_text = str(cue.get("text", "")).strip()
            should_flush = gap > max_gap or duration > max_duration
            if not should_flush and SOFT_END_RE.search(current_text) and not DEPENDENT_START_RE.search(next_text) and duration > 8:
                should_flush = True
            if should_flush:
                sentences.append(_make_sentence(len(sentences) + 1, current))
                current = []
        current.append(cue)
        text = " ".join(str(item["text"]).strip() for item in current).strip()
        duration = float(current[-1]["end"]) - float(current[0]["start"])
        if END_RE.search(text) and duration >= 1.0:
            sentences.append(_make_sentence(len(sentences) + 1, current))
            current = []
    if current:
        sentences.append(_make_sentence(len(sentences) + 1, current))
    return {"success": True, "backend": "sentence_segmenter_zh_en", "data": {"sentences": sentences, "sentence_count": len(sentences)}}


def _make_sentence(idx: int, cues: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(str(item["text"]).strip() for item in cues).strip()
    start = float(cues[0]["start"])
    end = float(cues[-1]["end"])
    return {
        "sentence_id": f"sent_{idx:04}",
        "start": round(start, 3),
        "end": round(end, 3),
        "text": text,
        "duration": round(end - start, 3),
        "source_cue_ids": [item.get("cue_id", f"cue_{i}") for i, item in enumerate(cues, start=1)],
    }

