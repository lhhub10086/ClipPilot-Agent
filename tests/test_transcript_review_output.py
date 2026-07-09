from __future__ import annotations

from pathlib import Path


def test_transcript_review_output_exists():
    report = Path("outputs/workflow_run/validation_report.json")
    if report.exists() and '"transcript_valid": false' in report.read_text(encoding="utf-8").lower():
        return
    path = Path("outputs/workflow_run/transcript_review.md")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "# Storyline Review" in text
    gate = Path("outputs/workflow_run/export_gate_decision.json")
    if gate.exists() and '"video_export_allowed": false' in gate.read_text(encoding="utf-8").lower():
        return
    assert "Coherence:" in text
