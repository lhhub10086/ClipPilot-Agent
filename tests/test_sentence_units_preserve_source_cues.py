from clip_pilot.tools.subtitle_refinement_tool import refine_segments


def test_sentence_units_preserve_source_cues(tmp_path):
    raw = [{"start": 0.0, "end": 2.0, "text": "今天讲加速度"}, {"start": 2.0, "end": 5.0, "text": "它描述速度变化快慢。"}]
    result = refine_segments(raw, str(tmp_path))
    units = result["data"]["sentence_units"]

    assert units[0]["source_cue_ids"]
    assert units[0]["timing_source"] == "raw_asr_cue_boundaries"
