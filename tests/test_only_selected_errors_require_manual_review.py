import csv
import json

from clip_pilot.tools.selection_scope_transcript_gate import run_selection_scope_gate


def test_only_selected_errors_are_marked_required_for_current_edit(tmp_path):
    blocks = tmp_path / "blocks.json"
    risks = tmp_path / "risks.json"
    units = tmp_path / "units.json"
    review_csv = tmp_path / "review.csv"
    blocks.write_text(json.dumps({"semantic_blocks": [{"block_id": "b1", "sentence_ids": ["s1"]}, {"block_id": "b2", "sentence_ids": ["s2"]}]}), encoding="utf-8")
    risks.write_text(json.dumps({"risks": [{"sentence_id": "s1", "start": 0, "end": 1, "risk_score": 1.0, "text": "bad1"}, {"sentence_id": "s2", "start": 2, "end": 3, "risk_score": 1.0, "text": "bad2"}]}), encoding="utf-8")
    units.write_text(json.dumps({"sentence_units": [{"sentence_id": "s1", "start": 0, "end": 1, "refined_text": "bad1"}, {"sentence_id": "s2", "start": 2, "end": 3, "refined_text": "bad2"}]}), encoding="utf-8")

    run_selection_scope_gate(
        selector_response={"selected_topics": [{"candidate_block_ids": ["b1"]}]},
        semantic_blocks_path=str(blocks),
        editing_units_path=None,
        asr_risk_report_path=str(risks),
        transcript_resolution_path=None,
        output_path=str(tmp_path / "scope.json"),
        sentence_units_path=str(units),
        manual_review_csv_path=str(review_csv),
        generate_audio_assets=False,
    )
    rows = list(csv.DictReader(review_csv.open(encoding="utf-8-sig")))
    required = {row["sentence_id"]: row["required_for_current_edit"] for row in rows}
    assert required["s1"] == "True"
    assert required["s2"] == "False"
