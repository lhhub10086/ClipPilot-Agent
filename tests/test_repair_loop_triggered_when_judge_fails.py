import json

from clip_pilot.harness.artifact_validator import ArtifactValidator


def _base_run(root, *, repair_rounds=1, allowed=False):
    steps = [
        "input_validation",
        "intent_parse",
        "subtitle_parse",
        "transcript_quality_check",
        "selector_llm_call",
        "editor_llm_call",
        "final_review_transcript_generation",
        "judge_llm_call_round_1",
        "timeline_repair_round_1",
        "judge_llm_call_round_2",
        "export_gate_decision",
        "artifact_validation",
    ]
    (root / "trace.json").write_text(json.dumps({"steps": [_step(name) for name in steps]}), encoding="utf-8")
    (root / "workflow_summary.json").write_text("{}", encoding="utf-8")
    (root / "transcript_quality_report.json").write_text(json.dumps({"transcript_valid": True}), encoding="utf-8")
    (root / "selector_response.json").write_text("{}", encoding="utf-8")
    (root / "editor_timeline.json").write_text("{}", encoding="utf-8")
    (root / "final_review_transcript.md").write_text("draft", encoding="utf-8")
    (root / "judge_response_round_1.json").write_text(json.dumps({"passed": False, "score": 0.4, "major_problems": [{"type": "topic_jump"}]}), encoding="utf-8")
    (root / "policy_validation_report.json").write_text(json.dumps({"policy_valid": True, "violations": []}), encoding="utf-8")
    (root / "export_gate_decision.json").write_text(
        json.dumps(
            {
                "video_export_allowed": allowed,
                "export_requested": False,
                "repair_rounds": repair_rounds,
                "judge_final_score": 0.8 if allowed else 0.4,
                "content_valid": allowed,
                "policy_valid": True,
                "policy_violations": [],
            }
        ),
        encoding="utf-8",
    )
    repair_dir = root / "repair_round_1"
    repair_dir.mkdir()
    (repair_dir / "editor_timeline.json").write_text("{}", encoding="utf-8")
    (repair_dir / "final_review_transcript.md").write_text("repaired", encoding="utf-8")
    (repair_dir / "repair_actions_applied.json").write_text(json.dumps({"timeline_changed": True}), encoding="utf-8")
    (repair_dir / "judge_response.json").write_text(json.dumps({"passed": allowed, "score": 0.8 if allowed else 0.4}), encoding="utf-8")


def _step(name):
    return {"step_name": name, "tool_name": name, "success": True, "input_summary": {}, "output_summary": {"timeline_changed": name.startswith("timeline_repair")}, "output_path": "", "error": None, "duration_seconds": 0.0}


def test_repair_loop_triggered_when_judge_fails(tmp_path):
    _base_run(tmp_path, repair_rounds=1, allowed=True)
    report = ArtifactValidator().validate(str(tmp_path))
    checks = {item["name"]: item["passed"] for item in report["checks"]}
    assert checks["repair_loop_triggered_when_judge_failed"] is True
    assert checks["no_direct_block_on_first_judge_failure_when_transcript_valid"] is True
