import csv
import json

from scripts.apply_subtitle_review import apply_review


def test_review_preserves_original_timing_contract(tmp_path):
    review_csv = tmp_path / "review.csv"
    units = tmp_path / "units.json"
    blocks = tmp_path / "blocks.json"
    with review_csv.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["sentence_id", "corrected_text", "review_status"])
        writer.writeheader()
        writer.writerow({"sentence_id": "sentence_001", "corrected_text": "人工确认后的句子。", "review_status": "approved"})
    units.write_text(json.dumps({"sentence_units": [{"sentence_id": "sentence_001", "start": 10.5, "end": 15.25, "refined_text": "坏句子。", "text": "坏句子。", "source_cue_ids": ["cue_1", "cue_2"], "sentence_complete": True}]}), encoding="utf-8")
    blocks.write_text(json.dumps({"semantic_blocks": [{"block_id": "block_001", "sentence_ids": ["sentence_001"], "text": "坏句子。"}]}), encoding="utf-8")

    result = apply_review(review_csv=str(review_csv), sentence_units_path=str(units), semantic_blocks_path=str(blocks), output_dir=str(tmp_path / "out"))
    reviewed = json.loads(open(result["sentence_units_reviewed"], encoding="utf-8").read())["sentence_units"][0]
    assert reviewed["start"] == 10.5
    assert reviewed["end"] == 15.25
    assert reviewed["source_cue_ids"] == ["cue_1", "cue_2"]
