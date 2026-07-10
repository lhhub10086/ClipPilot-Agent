from __future__ import annotations

import json
from pathlib import Path


def test_final_review_does_not_use_opencv_fallback():
    trace = json.loads(Path("tests/fixtures/bad_transcript_run/trace.json").read_text(encoding="utf-8"))
    if not any(step["step_name"] == "final_review_video_generation" for step in trace["steps"]):
        return
    final_step = next(step for step in trace["steps"] if step["step_name"] == "final_review_video_generation")
    assert final_step["output_summary"]["backend"] == "ffmpeg_concat"
    assert "opencv" not in json.dumps(final_step, ensure_ascii=False).lower()
    assert Path("outputs/workflow_run/logs/final_video_ffmpeg.log").exists()
