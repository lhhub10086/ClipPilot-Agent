from clip_pilot.harness.artifact_validator import ArtifactValidator
from test_repair_loop_triggered_when_judge_fails import _base_run


def test_judge_recalled_after_repair(tmp_path):
    _base_run(tmp_path, repair_rounds=1, allowed=True)
    report = ArtifactValidator().validate(str(tmp_path))
    checks = {item["name"]: item["passed"] for item in report["checks"]}
    assert checks["judge_recalled_after_repair"] is True
