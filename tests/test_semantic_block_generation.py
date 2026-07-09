from __future__ import annotations

from clip_pilot.tools.semantic_block_tool import build_blocks


def test_semantic_blocks_use_complete_sentences():
    sentences = [
        {"sentence_id": "s1", "start": 0, "end": 5, "text": "A definition explains the concept."},
        {"sentence_id": "s2", "start": 5, "end": 10, "text": "This example helps students understand."},
    ]
    blocks = build_blocks(sentences)["data"]["blocks"]
    assert blocks
    assert blocks[0]["starts_mid_sentence"] is False
    assert blocks[0]["ends_mid_sentence"] is False
    assert blocks[0]["duration"] >= 8
