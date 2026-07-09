import json

from eval.build_human_review_sheet import build_sheet


def test_blind_review_sheet_hides_system_name(tmp_path):
    raw = tmp_path / "raw.jsonl"
    raw.write_text(
        json.dumps(
            {
                "case_id": "c1",
                "system_name": "multi_agent_harness",
                "category": "good_vtt",
                "language": "en",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "sheet.csv"
    build_sheet(raw, output)
    text = output.read_text(encoding="utf-8")
    assert "system_name" not in text
    assert "multi_agent_harness" not in text
    assert "output_id" in text
