from clip_pilot.agent import subtitle_refiner


def test_llm_generated_timestamps_are_ignored(monkeypatch, tmp_path):
    def fake_call(messages, config):
        return {
            "success": True,
            "model": "fake",
            "json": {
                "sentence_units": [
                    {
                        "source_cue_ids": ["cue_0001", "cue_0002"],
                        "start": 999.0,
                        "end": 1000.0,
                        "refined_text": "一节课不能讲完整个高中物理。",
                        "sentence_complete": True,
                        "corrections": [],
                    }
                ],
                "unresolved_items": [],
            },
            "token_proxy": 10,
        }

    monkeypatch.setattr(subtitle_refiner, "call_chat_completion", fake_call)
    result = subtitle_refiner.refine_cues_with_llm(
        raw_cues=[
            {"cue_id": "cue_0001", "start": 6.0, "end": 8.0, "raw_text": "因为一节课"},
            {"cue_id": "cue_0002", "start": 8.0, "end": 12.0, "raw_text": "不能讲完整个高中物理"},
        ],
        output_dir=str(tmp_path),
        config={"llm": {"model": "fake"}},
        domain_glossary=["高中物理"],
    )
    unit = result["data"]["sentence_units"][0]
    assert unit["start"] == 6.0
    assert unit["end"] == 12.0
    assert unit["timing_source"] == "raw_asr_cue_boundaries"
