from clip_pilot.agent import subtitle_refiner


def test_subtitle_refiner_llm_called(monkeypatch, tmp_path):
    calls = []

    def fake_call(messages, config):
        calls.append(messages)
        return {
            "success": True,
            "model": "fake",
            "json": {"sentence_units": [{"source_cue_ids": ["cue_0001"], "refined_text": "今天讲加速度。", "sentence_complete": True, "corrections": []}], "unresolved_items": []},
            "token_proxy": 10,
        }

    monkeypatch.setattr(subtitle_refiner, "call_chat_completion", fake_call)
    result = subtitle_refiner.refine_cues_with_llm(
        raw_cues=[{"cue_id": "cue_0001", "start": 0.0, "end": 4.0, "raw_text": "今天讲加速度"}],
        output_dir=str(tmp_path),
        config={"llm": {"model": "fake"}},
        domain_glossary=["加速度"],
    )

    assert calls
    assert result["data"]["llm_called"] is True
    assert result["backend"] == "llm"
