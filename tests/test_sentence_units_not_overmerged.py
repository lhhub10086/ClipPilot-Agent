from clip_pilot.tools.subtitle_refinement_tool import refine_segments


def test_first_18_seconds_not_one_overmerged_sentence_unit(tmp_path):
    raw = [
        {"start": 0.0, "end": 4.0, "text": "今天呢,我不為了要講任何的物理知識"},
        {"start": 4.0, "end": 6.0, "text": "講沒有意義"},
        {"start": 6.0, "end": 10.0, "text": "因為我一進二後我也不可能把高中物理給你們講完"},
        {"start": 10.0, "end": 13.0, "text": "講一點點知識給你們來講也沒有什麼用"},
        {"start": 13.0, "end": 17.0, "text": "那麼今天呢,我想給大家講三個問題"},
    ]
    result = refine_segments(raw, str(tmp_path))
    assert len(result["data"]["sentence_units"]) >= 2
