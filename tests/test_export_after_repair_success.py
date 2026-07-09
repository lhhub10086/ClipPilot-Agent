from clip_pilot.harness.artifact_validator import ArtifactValidator
from test_repair_loop_triggered_when_judge_fails import _base_run


def test_export_allowed_after_repair_success(tmp_path):
    _base_run(tmp_path, repair_rounds=1, allowed=True)
    report = ArtifactValidator().validate(str(tmp_path))
    assert report["content_valid"] is True
    assert report["video_export_allowed"] is True
    assert report["harness_behavior_valid"] is True
