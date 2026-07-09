import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "workflow_run"


def test_workflow_summary_primary_outputs():
    summary = json.loads((OUT / "workflow_summary.json").read_text(encoding="utf-8"))
    if summary.get("export_video"):
        assert summary["primary_outputs"] == ["final_review.mp4", "timeline.json", "edit_plan.json", "human_review_sheet.csv"]
    elif not summary["transcript_valid"]:
        assert summary["primary_outputs"] == ["transcript_quality_report.json", "export_gate_decision.json"]
    else:
        assert summary["primary_outputs"] == [
            "selector_response.json",
            "editor_timeline.json",
            "final_review_transcript.md",
            "judge_response_round_1.json",
            "export_gate_decision.json",
        ]
    assert "validation_report.json" in summary["supporting_outputs"]
