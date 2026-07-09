from pathlib import Path

from clip_pilot.tools import subtitle_tool


def test_refined_asr_cache_is_returned_before_raw_cache(tmp_path: Path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake-video")
    cache = tmp_path / "cache.vtt"
    cache.write_text("WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\n短句\n\n2\n00:00:02.000 --> 00:00:04.000\n继续讲。\n", encoding="utf-8")
    monkeypatch.setattr(subtitle_tool, "extract_embedded_subtitle", lambda *_args, **_kwargs: {"success": False})
    monkeypatch.setattr(subtitle_tool, "asr_cache_path", lambda *_args, **_kwargs: cache)

    result = subtitle_tool.load_or_transcribe(str(video), None, str(tmp_path / "out"), {"asr": {"language": "zh"}})

    assert result["success"] is True
    assert result["backend"] == "refined_asr_cache"
    assert result["output_path"].endswith("refined_subtitle.vtt")
