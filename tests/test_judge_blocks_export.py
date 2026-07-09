import json

from clip_pilot.harness.artifact_validator import ArtifactValidator
from clip_pilot.schemas.trace_schema import REQUIRED_TRACE_STEPS


def _write_trace(root):
    steps = []
    for name in REQUIRED_TRACE_STEPS:
        steps.append(
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
        )
    (root / "trace.json").write_text(json.dumps({"steps": steps}, ensure_ascii=False), encoding="utf-8")


def test_judge_failure_blocks_video_export(tmp_path):
    _write_trace(tmp_path)
    (tmp_path / "selector_response.json").write_text('{"selected_topics":[]}', encoding="utf-8")
    (tmp_path / "editor_timeline.json").write_text('{"timeline_items":[]}', encoding="utf-8")
    (tmp_path / "final_review_transcript.md").write_text("bad transcript", encoding="utf-8")
    (tmp_path / "judge_response_round_1.json").write_text(
        json.dumps({"passed": False, "score": 0.4, "major_problems": [{"type": "topic_jump"}]}),
        encoding="utf-8",
    )
    (tmp_path / "export_gate_decision.json").write_text(
        json.dumps({"video_export_allowed": False, "export_requested": True, "judge_final_score": 0.4, "judge_passed": False, "repair_rounds": 0}),
        encoding="utf-8",
    )
    (tmp_path / "transcript_quality_report.json").write_text(json.dumps({"transcript_valid": True}), encoding="utf-8")
    (tmp_path / "workflow_summary.json").write_text(json.dumps({"primary_outputs": []}), encoding="utf-8")

    report = ArtifactValidator().validate(str(tmp_path))
    assert report["harness_behavior_valid"] is False
    check_map = {item["name"]: item["passed"] for item in report["checks"]}
    assert check_map["no_video_export_when_gate_false"] is True
    assert check_map["no_direct_block_on_first_judge_failure_when_transcript_valid"] is False
    assert not (tmp_path / "final_review.mp4").exists()
