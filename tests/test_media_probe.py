from __future__ import annotations

from pathlib import Path

from clip_pilot.tools.media_probe_tool import probe_media


def test_media_probe_reports_final_review_quality():
    path = Path("outputs/workflow_run/final_review.mp4")
    if not path.exists():
        return
    probe = probe_media(str(path))
    assert probe["exists"] is True
    assert probe["frame_count"] > 0
    assert probe["width"] > 0 and probe["height"] > 0
    assert "black_frame_ratio" in probe
