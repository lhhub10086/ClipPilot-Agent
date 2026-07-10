import json
from pathlib import Path

from clip_pilot.harness import ArtifactValidator


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "bad_transcript_run"


def test_artifact_validator_passes_workflow_run():
    report = ArtifactValidator().validate(str(OUT))
    assert report["run_completed"] is True
    assert report["harness_behavior_valid"] is True
    check_map = {item["name"]: item["passed"] for item in report["checks"]}
    assert check_map["transcript_quality_report_exists"] is True
