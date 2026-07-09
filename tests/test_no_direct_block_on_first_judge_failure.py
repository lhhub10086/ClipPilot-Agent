import json

from clip_pilot.harness.artifact_validator import ArtifactValidator


def test_no_direct_block_on_first_judge_failure(tmp_path):
    steps = ["input_validation", "subtitle_parse", "transcript_quality_check", "selector_llm_call", "editor_llm_call", "judge_llm_call_round_1", "export_gate_decision", "artifact_validation"]
    (tmp_path / "trace.json").write_text(json.dumps({"steps": [_step(name) for name in steps]}), encoding="utf-8")
    (tmp_path / "workflow_summary.json").write_text("{}", encoding="utf-8")
    (tmp_path / "transcript_quality_report.json").write_text(json.dumps({"transcript_valid": True}), encoding="utf-8")
    for name in ["selector_response.json", "editor_timeline.json", "final_review_transcript.md"]:
        (tmp_path / name).write_text("{}", encoding="utf-8")
    (tmp_path / "judge_response_round_1.json").write_text(json.dumps({"passed": False, "score": 0.4, "major_problems": [{"type": "topic_jump"}]}), encoding="utf-8")
    (tmp_path / "export_gate_decision.json").write_text(json.dumps({"video_export_allowed": False, "export_requested": False, "repair_rounds": 0}), encoding="utf-8")
    report = ArtifactValidator().validate(str(tmp_path))
    checks = {item["name"]: item["passed"] for item in report["checks"]}
    assert checks["no_direct_block_on_first_judge_failure_when_transcript_valid"] is False


def _step(name):
    return {"step_name": name, "tool_name": name, "success": True, "input_summary": {}, "output_summary": {}, "output_path": "", "error": None, "duration_seconds": 0.0}
