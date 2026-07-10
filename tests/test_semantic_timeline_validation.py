from __future__ import annotations

import json
from pathlib import Path


def test_semantic_timeline_validation_passes_current_dry_run():
    report = json.loads(Path("tests/fixtures/bad_transcript_run/validation_report.json").read_text(encoding="utf-8"))
    summary = json.loads(Path("tests/fixtures/bad_transcript_run/workflow_summary.json").read_text(encoding="utf-8"))
    checks = report["checks"]
    assert summary["multi_agent_loop"] is True
    assert "semantic_timeline_valid" in summary
    check_map = {item["name"]: item["passed"] for item in checks}
    if "semantic_timeline_valid" in check_map:
        assert check_map["semantic_timeline_valid"] is True
        assert check_map["video_export_blocked_in_dry_run"] is True
    elif not report["transcript_valid"]:
        assert report["blocked_reason"] == "transcript_quality_failed"
    else:
        assert check_map["export_gate_decision_exists"] is True
        assert check_map["no_video_export_when_gate_false"] is True
