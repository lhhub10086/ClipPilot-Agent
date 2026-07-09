from pathlib import Path

from clip_pilot.workflows.content_review_workflow import write_export_gate


class DummyContext:
    def __init__(self, root: Path, policy_valid: bool):
        self.root = root
        self.state = {
            "final_judge_response": {"passed": True, "score": 0.9, "major_problems": [], "reason": "ok"},
            "policy_valid": policy_valid,
            "policy_validation_report": {"violations": [] if policy_valid else [{"type": "final_duration_exceeds_policy", "severity": "blocking"}]},
            "repair_loop_triggered": False,
            "repair_rounds": 0,
            "repair_success": policy_valid,
            "export_video": True,
        }

    def output_path(self, name: str) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root / name


def test_policy_valid_is_required_for_export(tmp_path: Path):
    blocked = write_export_gate(DummyContext(tmp_path / "blocked", policy_valid=False))["data"]["export_gate_decision"]
    allowed = write_export_gate(DummyContext(tmp_path / "allowed", policy_valid=True))["data"]["export_gate_decision"]

    assert blocked["video_export_allowed"] is False
    assert allowed["video_export_allowed"] is True
