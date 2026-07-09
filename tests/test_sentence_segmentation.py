from __future__ import annotations

from clip_pilot.tools.sentence_segment_tool import build_sentences


def test_sentence_segmentation_merges_cues_to_complete_sentence():
    cues = [
        {"start": 0, "end": 1, "text": "This is"},
        {"start": 1, "end": 2, "text": "a complete idea."},
        {"start": 3, "end": 4, "text": "Next point."},
    ]
    sentences = build_sentences(cues)["data"]["sentences"]
    assert sentences[0]["start"] == 0
    assert sentences[0]["end"] == 2
    assert sentences[0]["text"].endswith(".")
