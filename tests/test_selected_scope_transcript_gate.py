import json

from clip_pilot.tools.selection_scope_transcript_gate import run_selection_scope_gate


def test_selected_scope_transcript_gate_blocks_selected_unresolved(tmp_path):
    blocks = tmp_path / "blocks.json"
    risks = tmp_path / "risks.json"
    blocks.write_text(json.dumps({"semantic_blocks": [{"block_id": "risky", "sentence_ids": ["s2"]}]}), encoding="utf-8")
    risks.write_text(json.dumps({"risks": [{"sentence_id": "s2", "risk_score": 1.0, "text": "bad"}]}), encoding="utf-8")

    result = run_selection_scope_gate(
        selector_response={"selected_topics": [{"candidate_block_ids": ["risky"]}]},
        semantic_blocks_path=str(blocks),
        editing_units_path=None,
        asr_risk_report_path=str(risks),
        transcript_resolution_path=None,
        output_path=str(tmp_path / "scope.json"),
        generate_audio_assets=False,
    )

    assert result["data"]["selected_scope_lexical_valid"] is False
    assert result["data"]["selected_scope_unresolved_count"] == 1
    assert result["data"]["editing_allowed"] is False
