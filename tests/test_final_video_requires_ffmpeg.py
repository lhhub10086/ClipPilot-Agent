from __future__ import annotations

from clip_pilot.tools import final_video_tool


def test_final_video_generation_fails_without_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(final_video_tool, "resolve_ffmpeg", lambda: None)
    result = final_video_tool.generate_final_review([], str(tmp_path / "final.mp4"), str(tmp_path / "temp"))
    assert result["success"] is False
    assert "ffmpeg unavailable" in result["error"]
