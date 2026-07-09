import json
from pathlib import Path


OUT = Path("outputs/workflow_run")


def test_bad_transcript_run_stops_before_multi_agent_loop():
    report = json.loads((OUT / "validation_report.json").read_text(encoding="utf-8"))
    trace = json.loads((OUT / "trace.json").read_text(encoding="utf-8"))
    steps = {step["step_name"] for step in trace["steps"]}

    assert report["run_completed"] is True
    assert report["transcript_valid"] is False
    assert report["blocked_reason"] == "transcript_quality_failed"
    assert "transcript_quality_check" in steps
    assert "selector_llm_call" not in steps
    assert "editor_llm_call" not in steps
    assert "judge_llm_call" not in steps
