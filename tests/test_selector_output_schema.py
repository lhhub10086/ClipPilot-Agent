from clip_pilot.agent import content_selector


def test_content_selector_writes_raw_and_parsed_response(tmp_path, monkeypatch):
    def fake_call(messages, llm_config):
        return {
            "success": True,
            "backend": "llm_api",
            "model": "fake-model",
            "json": {
                "selected_topics": [
                    {
                        "topic_id": "topic_001",
                        "topic_title": "核心概念",
                        "importance_reason": "完整解释了关键知识点",
                        "candidate_block_ids": ["block_001"],
                        "priority": 1,
                    }
                ],
                "discarded_blocks": [{"block_id": "block_002", "reason": "filler"}],
            },
            "content": "{}",
        }

    monkeypatch.setattr(content_selector, "call_chat_completion", fake_call)
    blocks = [
        {
            "block_id": "block_001",
            "start": 1.0,
            "end": 12.0,
            "text": "A complete explanation.",
            "block_type": "explanation",
            "completeness_score": 0.9,
            "standalone_score": 0.8,
        }
    ]

    result = content_selector.run_content_selector(
        intent="make a coherent course review",
        video_metadata={"video_path": "demo.mp4"},
        semantic_blocks=blocks,
        config={"llm": {"model": "fake-model"}},
        output_dir=str(tmp_path),
    )

    assert result["success"] is True
    assert (tmp_path / "selector_raw_response.json").exists()
    assert (tmp_path / "selector_response.json").exists()
    assert result["data"]["selector_response"]["selected_topics"][0]["candidate_block_ids"] == ["block_001"]
