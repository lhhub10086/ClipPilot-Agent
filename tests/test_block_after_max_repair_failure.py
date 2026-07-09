import json

from clip_pilot.harness.artifact_validator import ArtifactValidator
from test_repair_loop_triggered_when_judge_fails import _step


def test_block_after_max_repair_failure(tmp_path):
    steps = ["input_validation", "subtitle_parse", "transcript_quality_check", "selector_llm_call", "editor_llm_call", "judge_llm_call_round_1"]
    for idx in range(1, 4):
        steps.extend([f"timeline_repair_round_{idx}", f"judge_llm_call_round_{idx + 1}"])
    steps.extend(["export_gate_decision", "artifact_validation"])
    (tmp_path / "trace.json").write_text(json.dumps({"steps": [_step(name) for name in steps]}), encoding="utf-8")
    (tmp_path / "workflow_summary.json").write_text("{}", encoding="utf-8")
    (tmp_path / "transcript_quality_report.json").write_text(json.dumps({"transcript_valid": True}), encoding="utf-8")
    for name in ["selector_response.json", "editor_timeline.json", "final_review_transcript.md"]:
        (tmp_path / name).write_text("{}", encoding="utf-8")
    (tmp_path / "judge_response_round_1.json").write_text(json.dumps({"passed": False, "score": 0.4, "major_problems": [{"type": "topic_jump"}]}), encoding="utf-8")
    (tmp_path / "export_gate_decision.json").write_text(json.dumps({"video_export_allowed": False, "export_requested": False, "repair_rounds": 3, "blocked_reason": "coherence_judge_failed_after_repair"}), encoding="utf-8")
    for idx in range(1, 4):
        repair_dir = tmp_path / f"repair_round_{idx}"
        repair_dir.mkdir()
        (repair_dir / "editor_timeline.json").write_text("{}", encoding="utf-8")
        (repair_dir / "final_review_transcript.md").write_text("repaired", encoding="utf-8")
        (repair_dir / "repair_actions_applied.json").write_text(json.dumps({"timeline_changed": True}), encoding="utf-8")
        (repair_dir / "judge_response.json").write_text(json.dumps({"passed": False, "score": 0.4}), encoding="utf-8")
    report = ArtifactValidator().validate(str(tmp_path))
    checks = {item["name"]: item["passed"] for item in report["checks"]}
    assert report["video_export_allowed"] is False
    assert checks["export_blocked_only_after_max_repair_if_transcript_valid"] is True
