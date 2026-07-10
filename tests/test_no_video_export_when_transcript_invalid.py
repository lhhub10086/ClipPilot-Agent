import json
from pathlib import Path


def test_no_video_export_when_transcript_invalid():
    out = Path("tests/fixtures/bad_transcript_run")
    report = json.loads((out / "validation_report.json").read_text(encoding="utf-8"))
    assert report["transcript_valid"] is False
    assert report["video_export_allowed"] is False
    assert report["video_exported"] is False
    assert not (out / "final_review.mp4").exists()
