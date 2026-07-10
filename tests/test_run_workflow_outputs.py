import csv
import json
from pathlib import Path

from clip_pilot.schemas import REQUIRED_TRACE_STEPS, validate_edit_plan, validate_trace


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "bad_transcript_run"


def test_run_workflow_outputs_exist():
    summary = json.loads((OUT / "workflow_summary.json").read_text(encoding="utf-8"))
    if summary["transcript_valid"]:
        names = ["selector_response.json", "editor_timeline.json", "final_review_transcript.md", "judge_response_round_1.json", "export_gate_decision.json"]
    else:
        names = ["transcript_quality_report.json", "export_gate_decision.json"]
    for name in [*names, "trace.json", "workflow_summary.json", "validation_report.json"]:
        assert (OUT / name).exists(), name


def test_run_workflow_contracts():
    trace = json.loads((OUT / "trace.json").read_text(encoding="utf-8"))
    validation = json.loads((OUT / "validation_report.json").read_text(encoding="utf-8"))
    assert validate_trace(trace) == []
    present = {step["step_name"] for step in trace["steps"]}
    assert {"input_validation", "intent_parse", "subtitle_parse", "transcript_quality_check", "artifact_validation"}.issubset(present)
    if validation["transcript_valid"]:
        assert set(REQUIRED_TRACE_STEPS).issubset(present)
    assert validation["harness_behavior_valid"] is True


def test_review_sheet_fields():
    if not (OUT / "human_review_sheet.csv").exists():
        return
    with (OUT / "human_review_sheet.csv").open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows
    assert {"clip_id", "title", "reason", "review_question", "clip_suggestion", "reviewer_score", "accepted", "comment"}.issubset(rows[0])
