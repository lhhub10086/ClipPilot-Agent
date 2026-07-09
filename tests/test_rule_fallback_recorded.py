from clip_pilot.agent import subtitle_refiner


def test_rule_fallback_recorded_when_llm_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(subtitle_refiner, "call_chat_completion", lambda *_args, **_kwargs: {"success": False, "error": "boom", "token_proxy": 0})
    result = subtitle_refiner.refine_cues_with_llm(
        raw_cues=[{"cue_id": "cue_0001", "start": 0.0, "end": 4.0, "raw_text": "今天讲加速度"}],
        output_dir=str(tmp_path),
        config={"llm": {"model": "fake"}},
        domain_glossary=["加速度"],
    )
    assert result["backend"] == "llm_with_rule_preprocess"
    assert result["data"]["fallback_used"] is True
