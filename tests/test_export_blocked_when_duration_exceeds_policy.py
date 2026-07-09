from pathlib import Path

from clip_pilot.workflows.content_review_workflow import write_export_gate


class DummyContext:
    def __init__(self, root: Path):
        self.root = root
        self.state = {
            "final_judge_response": {"passed": True, "score": 0.95, "major_problems": [], "reason": "coherent"},
            "policy_valid": False,
            "policy_validation_report": {"violations": [{"type": "final_duration_exceeds_policy", "severity": "blocking"}]},
            "repair_loop_triggered": True,
            "repair_rounds": 3,
            "repair_success": False,
            "export_video": True,
        }

    def output_path(self, name: str) -> Path:
        return self.root / name


def test_export_gate_blocks_when_policy_invalid(tmp_path: Path):
    result = write_export_gate(DummyContext(tmp_path))
    gate = result["data"]["export_gate_decision"]

    assert gate["content_valid"] is True
    assert gate["policy_valid"] is False
    assert gate["video_export_allowed"] is False
    assert gate["blocked_reason"] == "policy_violation"
