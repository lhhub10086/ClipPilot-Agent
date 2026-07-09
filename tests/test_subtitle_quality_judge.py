from clip_pilot.agent import subtitle_quality_judge


def test_subtitle_quality_judge_runs_with_fake_llm(monkeypatch, tmp_path):
    def fake_call(messages, config):
        return {"success": True, "model": "fake", "json": {"passed": True, "score": 0.88, "problems": [], "repair_instructions": []}, "token_proxy": 5}

    monkeypatch.setattr(subtitle_quality_judge, "call_chat_completion", fake_call)
    result = subtitle_quality_judge.judge_subtitle_quality(
        raw_cues=[{"cue_id": "cue_0001", "start": 0, "end": 5, "raw_text": "今天讲加速度"}],
        sentence_units=[{"sentence_id": "sentence_0001", "start": 0, "end": 5, "duration": 5, "refined_text": "今天讲加速度。", "source_cue_ids": ["cue_0001"], "sentence_complete": True}],
        semantic_blocks=[],
        domain_glossary=["加速度"],
        output_dir=str(tmp_path),
        config={"llm": {"model": "fake"}},
    )
    assert result["data"]["judge_response"]["passed"] is True
    assert result["data"]["judge_response"]["score"] == 0.88
