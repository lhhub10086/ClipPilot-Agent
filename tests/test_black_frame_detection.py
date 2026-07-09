from __future__ import annotations

from pathlib import Path

from clip_pilot.tools.media_probe_tool import probe_media


def test_black_frame_detection_marks_black_video_invalid(tmp_path):
    import cv2
    import numpy as np

    path = tmp_path / "black.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24, (160, 90))
    for _ in range(48):
        writer.write(np.zeros((90, 160, 3), dtype=np.uint8))
    writer.release()
    probe = probe_media(str(path))
    assert probe["black_frame_ratio"] > 0.5
    assert probe["visual_valid"] is False
