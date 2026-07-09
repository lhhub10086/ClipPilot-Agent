import json

from clip_pilot.harness.artifact_validator import ArtifactValidator
from clip_pilot.schemas.trace_schema import REQUIRED_TRACE_STEPS


def test_gate_false_with_existing_video_fails_validation(tmp_path):
    steps = [
        {
            "step_name": name,
            "tool_name": name,
            "success": True,
            "input_summary": {},
            "output_summary": {},
            "output_path": "",
            "error": None,
            "duration_seconds": 0.0,
        }
        for name in REQUIRED_TRACE_STEPS
    ]
    (tmp_path / "trace.json").write_text(json.dumps({"steps": steps}), encoding="utf-8")
    for name in ["selector_response.json", "editor_timeline.json", "judge_response_round_1.json"]:
        (tmp_path / name).write_text("{}", encoding="utf-8")
    (tmp_path / "final_review_transcript.md").write_text("transcript", encoding="utf-8")
    (tmp_path / "export_gate_decision.json").write_text(
        json.dumps({"video_export_allowed": False, "export_requested": True, "judge_final_score": 0.3, "judge_passed": False, "repair_rounds": 0}),
        encoding="utf-8",
    )
    (tmp_path / "transcript_quality_report.json").write_text(json.dumps({"transcript_valid": True}), encoding="utf-8")
    (tmp_path / "final_review.mp4").write_bytes(b"not a valid deliverable")

    report = ArtifactValidator().validate(str(tmp_path))
    assert report["harness_behavior_valid"] is False
    check_map = {item["name"]: item["passed"] for item in report["checks"]}
    assert check_map["no_video_export_when_gate_false"] is False
