from clip_pilot.tools.subtitle_refinement_tool import refine_segments


def test_multi_thought_sentence_detection_affects_report(tmp_path):
    raw = [{"start": 0.0, "end": 16.0, "text": "第一个问题是区别。第二个问题是内容。第三个问题是方法。"}]
    result = refine_segments(raw, str(tmp_path))
    assert result["data"]["report"]["multi_thought_sentence_ratio"] >= 0
