from clip_pilot.workflows.content_review_workflow import write_export_gate


class DummyContext:
    def __init__(self, root, judge):
        self.root = root
        self.state = {"final_judge_response": judge, "policy_valid": True, "policy_validation_report": {"violations": []}, "repair_rounds": 1, "export_video": True}

    def output_path(self, name):
        return self.root / name


def test_export_gate_allows_only_passing_judge(tmp_path):
    passing = {"passed": True, "score": 0.82, "major_problems": []}
    result = write_export_gate(DummyContext(tmp_path, passing))
    gate = result["data"]["export_gate_decision"]
    assert gate["video_export_allowed"] is True
    assert gate["export_requested"] is True

    failing = {"passed": True, "score": 0.7, "major_problems": []}
    result = write_export_gate(DummyContext(tmp_path, failing))
    assert result["data"]["export_gate_decision"]["video_export_allowed"] is False
