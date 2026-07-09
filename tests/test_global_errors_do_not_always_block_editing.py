import json

from clip_pilot.tools.selection_scope_transcript_gate import run_selection_scope_gate


def test_global_errors_do_not_always_block_editing(tmp_path):
    blocks = tmp_path / "blocks.json"
    risks = tmp_path / "risks.json"
    resolution = tmp_path / "resolution.json"
    blocks.write_text(json.dumps({"semantic_blocks": [{"block_id": "safe", "sentence_ids": ["s1"]}, {"block_id": "risky", "sentence_ids": ["s2"]}]}), encoding="utf-8")
    risks.write_text(json.dumps({"risks": [{"sentence_id": "s2", "risk_score": 1.0, "text": "bad"}]}), encoding="utf-8")
    resolution.write_text(json.dumps({"resolutions": []}), encoding="utf-8")

    result = run_selection_scope_gate(
        selector_response={"selected_topics": [{"candidate_block_ids": ["safe"]}]},
        semantic_blocks_path=str(blocks),
        editing_units_path=None,
        asr_risk_report_path=str(risks),
        transcript_resolution_path=str(resolution),
        output_path=str(tmp_path / "scope.json"),
        generate_audio_assets=False,
    )

    data = result["data"]
    assert data["global_unresolved_count"] == 1
    assert data["selected_scope_unresolved_count"] == 0
    assert data["editing_allowed"] is True
    assert data["status"] == "auto_pass_with_exclusions"
