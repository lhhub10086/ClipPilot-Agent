import csv
import json
from pathlib import Path

from clip_pilot.tools import selection_scope_transcript_gate


def test_manual_review_audio_assets_generated_for_required_rows(monkeypatch, tmp_path):
    def fake_run(cmd, capture_output=True, text=True):
        Path(cmd[-1]).write_bytes(b"wav")
        class Completed:
            returncode = 0
            stderr = ""
        return Completed()

    monkeypatch.setattr(selection_scope_transcript_gate, "resolve_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(selection_scope_transcript_gate.subprocess, "run", fake_run)
    blocks = tmp_path / "blocks.json"
    risks = tmp_path / "risks.json"
    units = tmp_path / "units.json"
    review_csv = tmp_path / "review.csv"
    assets = tmp_path / "assets"
    blocks.write_text(json.dumps({"semantic_blocks": [{"block_id": "b1", "sentence_ids": ["s1"]}]}), encoding="utf-8")
    risks.write_text(json.dumps({"risks": [{"sentence_id": "s1", "start": 0, "end": 1, "risk_score": 1.0, "text": "bad"}]}), encoding="utf-8")
    units.write_text(json.dumps({"sentence_units": [{"sentence_id": "s1", "start": 0, "end": 1, "refined_text": "bad"}]}), encoding="utf-8")

    run = selection_scope_transcript_gate.run_selection_scope_gate(
        selector_response={"selected_topics": [{"candidate_block_ids": ["b1"]}]},
        semantic_blocks_path=str(blocks),
        editing_units_path=None,
        asr_risk_report_path=str(risks),
        transcript_resolution_path=None,
        output_path=str(tmp_path / "scope.json"),
        video_path=str(tmp_path / "video.mp4"),
        sentence_units_path=str(units),
        manual_review_csv_path=str(review_csv),
        manual_review_assets_dir=str(assets),
        generate_audio_assets=True,
    )
    rows = list(csv.DictReader(review_csv.open(encoding="utf-8-sig")))
    assert run["data"]["selected_scope_unresolved_count"] == 1
    assert rows[0]["audio_clip_path"]
    assert Path(rows[0]["audio_clip_path"]).exists()
