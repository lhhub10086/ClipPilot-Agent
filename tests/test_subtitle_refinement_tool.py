from pathlib import Path

from clip_pilot.tools.subtitle_refinement_tool import clean_text, refine_segments


def test_traditional_to_simplified_and_keyword_correction():
    text, corrections = clean_text("我們初農物理和高中物理的聯繫")
    assert "我们" in text
    assert "初中物理" in text
    assert "联系" in text
    assert corrections


def test_chinese_short_cue_merge(tmp_path: Path):
    raw = [
        {"start": 0.0, "end": 4.0, "text": "今天呢,我不為了要講任何的物理知識"},
        {"start": 4.0, "end": 6.0, "text": "講沒有意義"},
        {"start": 6.0, "end": 10.0, "text": "因為我一進二後我也不可能把高中物理給你們講完"},
    ]
    result = refine_segments(raw, str(tmp_path))
    refined = result["data"]["segments"]

    assert len(refined) == 1
    assert refined[0]["start"] == 0.0
    assert refined[0]["end"] == 10.0
    assert "讲这些没有意义" in refined[0]["text"]
    assert "一节课" in refined[0]["text"]


def test_refined_cues_are_not_mostly_too_short(tmp_path: Path):
    raw = [{"start": i * 2.0, "end": i * 2.0 + 2.0, "text": f"这是第{i}个短句"} for i in range(8)]
    result = refine_segments(raw, str(tmp_path))
    report = result["data"]["report"]

    assert report["short_cue_ratio"] < 0.5
    assert Path(result["data"]["srt_path"]).exists()
    assert Path(result["data"]["vtt_path"]).exists()
