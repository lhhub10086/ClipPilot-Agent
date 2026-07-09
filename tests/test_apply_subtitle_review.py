import csv
import json

from scripts.apply_subtitle_review import apply_review


def test_apply_subtitle_review_preserves_timestamps_and_source_cues(tmp_path):
    review_csv = tmp_path / "review.csv"
    units = tmp_path / "units.json"
    blocks = tmp_path / "blocks.json"
    with review_csv.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["sentence_id", "corrected_text", "review_status"])
        writer.writeheader()
        writer.writerow({"sentence_id": "s1", "corrected_text": "正确字幕。", "review_status": "approved"})
    units.write_text(json.dumps({"sentence_units": [{"sentence_id": "s1", "start": 1.0, "end": 3.0, "refined_text": "错误字幕。", "text": "错误字幕。", "source_cue_ids": ["c1"], "sentence_complete": True}]}), encoding="utf-8")
    blocks.write_text(json.dumps({"semantic_blocks": [{"block_id": "b1", "sentence_ids": ["s1"], "text": "错误字幕。"}]}), encoding="utf-8")

    result = apply_review(review_csv=str(review_csv), sentence_units_path=str(units), semantic_blocks_path=str(blocks), output_dir=str(tmp_path / "out"))
    reviewed = json.loads(open(result["sentence_units_reviewed"], encoding="utf-8").read())["sentence_units"][0]
    assert reviewed["refined_text"] == "正确字幕。"
    assert reviewed["start"] == 1.0
    assert reviewed["end"] == 3.0
    assert reviewed["source_cue_ids"] == ["c1"]
