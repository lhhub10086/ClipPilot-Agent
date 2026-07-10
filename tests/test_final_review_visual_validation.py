from __future__ import annotations

import json
from pathlib import Path


def test_final_review_visual_validation_must_pass():
    report = json.loads(Path("tests/fixtures/bad_transcript_run/validation_report.json").read_text(encoding="utf-8"))
    if "final_review_visual_valid" not in report.get("checks", {}):
        return
    checks = report["checks"]
    assert checks["final_review_probe_valid"] is True
    assert checks["final_review_visual_valid"] is True
    assert checks["final_review_black_ratio_below_threshold"] is True
    assert report["media_probes"]["final_review"]["black_frame_ratio"] < 0.5
