import json
from pathlib import Path


def test_validation_report_uses_separate_status_fields():
    report = json.loads(Path("tests/fixtures/bad_transcript_run/validation_report.json").read_text(encoding="utf-8"))
    for key in [
        "run_completed",
        "input_valid",
        "transcript_valid",
        "content_valid",
        "video_export_allowed",
        "video_exported",
        "harness_behavior_valid",
        "blocked_reason",
        "checks",
    ]:
        assert key in report
    assert "success" not in report
    assert report["run_completed"] is True
    assert report["harness_behavior_valid"] is True
