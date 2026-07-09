import csv
import json

from clip_pilot.agent.risk_coherence_repair import run_risk_coherence_repair


def test_targeted_review_for_required_bridge(tmp_path):
    sentence_units = tmp_path / "units.json"
    risks = tmp_path / "risks.json"
    sentence_units.write_text(json.dumps({"sentence_units": [{"sentence_id": "s1", "start": 1, "end": 2, "refined_text": "bad"}]}), encoding="utf-8")
    risks.write_text(json.dumps({"risks": [{"sentence_id": "s1", "start": 1, "end": 2, "risk_score": 0.7, "text": "bad"}]}), encoding="utf-8")
    gap = {"required_manual_review_sentence_ids": ["s1"], "gaps": []}
    timeline = {"timeline_items": [{"segment_id": "segment_001", "source_block_ids": ["b1"], "source_start": 0, "source_end": 10}]}
    blocks = [{"block_id": "b1", "start": 0, "end": 10, "text": "safe", "lexical_risk_level": "low_risk"}]
    result = run_risk_coherence_repair(editor_timeline=timeline, coherence_gap_report=gap, semantic_blocks=blocks, output_dir=str(tmp_path), sentence_units_path=str(sentence_units), asr_risk_report_path=str(risks))
    rows = list(csv.DictReader(open(result["data"]["manual_review_csv"], encoding="utf-8-sig")))
    assert rows[0]["required_for_current_edit"] == "True"
