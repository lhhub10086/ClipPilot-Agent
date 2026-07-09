from __future__ import annotations

from pathlib import Path

from clip_pilot.tools.media_probe_tool import probe_media


def test_selected_segments_are_reencoded_to_standard_profile():
    segment = Path("outputs/workflow_run/assets/selected_segments/selected_segment_001.mp4")
    if not segment.exists():
        return
    probe = probe_media(str(segment))
    assert probe["visual_valid"] is True
    assert probe["width"] == 640
    assert probe["height"] == 360
    assert abs(float(probe["fps"]) - 24.0) <= 0.5
    assert str(probe["video_codec"]).startswith("h264")
