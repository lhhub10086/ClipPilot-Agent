from clip_pilot.agent import timeline_editor


def test_timeline_editor_normalizes_to_complete_blocks(tmp_path, monkeypatch):
    def fake_call(messages, llm_config):
        return {
            "success": True,
            "backend": "llm_api",
            "model": "fake-model",
            "json": {
                "timeline_items": [
                    {
                        "segment_id": "segment_001",
                        "role": "core_concept",
                        "source_block_ids": ["block_001", "block_002"],
                        "source_start": 99,
                        "source_end": 100,
                        "transcript": "invented",
                        "why_included": "coherent concept",
                    }
                ],
                "editing_strategy": {"mode": "single_topic", "quality_over_count": True},
            },
            "content": "{}",
        }

    monkeypatch.setattr(timeline_editor, "call_chat_completion", fake_call)
    blocks = [
        {"block_id": "block_001", "start": 10.0, "end": 20.0, "duration": 10.0, "text": "First complete sentence.", "block_type": "definition", "completeness_score": 0.9, "standalone_score": 0.9},
        {"block_id": "block_002", "start": 20.0, "end": 32.0, "duration": 12.0, "text": "Second complete sentence.", "block_type": "example", "completeness_score": 0.8, "standalone_score": 0.8},
    ]

    result = timeline_editor.run_timeline_editor(
        intent="make a coherent review",
        selector_response={"selected_topics": [{"candidate_block_ids": ["block_001", "block_002"]}]},
        semantic_blocks=blocks,
        default_policy={},
        config={"llm": {"model": "fake-model"}},
        output_dir=str(tmp_path),
    )

    item = result["data"]["editor_timeline"]["timeline_items"][0]
    assert result["success"] is True
    assert item["source_start"] == 10.0
    assert item["source_end"] == 32.0
    assert item["transcript"] == "First complete sentence. Second complete sentence."
    assert (tmp_path / "editor_timeline.json").exists()
