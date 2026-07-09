from pathlib import Path

from clip_pilot.tools.subtitle_refinement_tool import refine_segments


def test_semantic_blocks_are_separate_from_refined_srt(tmp_path: Path):
    raw = [{"start": 0.0, "end": 5.0, "text": "今天讲加速度。"}, {"start": 5.0, "end": 10.0, "text": "它描述速度变化快慢。"}]
    result = refine_segments(raw, str(tmp_path))

    assert Path(result["data"]["srt_path"]).exists()
    assert Path(result["data"]["sentence_units_path"]).exists()
    assert Path(result["data"]["semantic_blocks_path"]).exists()
    assert result["data"]["semantic_blocks"]
