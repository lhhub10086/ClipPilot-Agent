from clip_pilot.agent.content_selector import run_content_selector


def test_selector_postprocess_marks_selected_risky_block(monkeypatch, tmp_path):
    def fake_call(_messages, _config):
        return {
            "success": True,
            "backend": "llm_api",
            "model": "fake",
            "json": {"selected_topics": [{"topic_id": "t1", "candidate_block_ids": ["b1"]}]},
        }

    monkeypatch.setattr("clip_pilot.agent.content_selector.call_chat_completion", fake_call)
    blocks = [
        {"block_id": "b1", "start": 0, "end": 10, "text": "bad", "block_type": "explanation", "contains_unresolved_asr": True, "unresolved_sentence_ids": ["s1"], "lexical_risk_score": 1.0, "safe_for_auto_edit": False},
        {"block_id": "b2", "start": 10, "end": 20, "text": "safe", "block_type": "explanation", "contains_unresolved_asr": False, "unresolved_sentence_ids": [], "safe_for_auto_edit": True},
    ]
    result = run_content_selector(intent="review", video_metadata={}, semantic_blocks=blocks, config={"llm": {}}, output_dir=str(tmp_path))
    selector = result["data"]["selector_response"]
    assert selector["requires_manual_review"] is True
    assert selector["selected_scope_unresolved_sentence_ids"] == ["s1"]
    assert any(item["block_id"] == "b2" for item in selector["excluded_due_to_asr_risk"]) is False
