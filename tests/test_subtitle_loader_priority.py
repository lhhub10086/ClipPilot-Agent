from pathlib import Path

from clip_pilot.tools import subtitle_tool


def test_asr_cache_key_includes_model_language_and_config(tmp_path: Path):
    video = tmp_path / "lesson.mp4"
    video.write_bytes(b"fake-video-bytes")
    base = {"asr": {"model_size": "tiny", "language": "zh", "task": "transcribe", "config_name": "a"}}
    model_changed = {"asr": {"model_size": "small", "language": "zh", "task": "transcribe", "config_name": "a"}}
    lang_changed = {"asr": {"model_size": "tiny", "language": "en", "task": "transcribe", "config_name": "a"}}

    assert subtitle_tool.asr_cache_path(str(video), base) != subtitle_tool.asr_cache_path(str(video), model_changed)
    assert subtitle_tool.asr_cache_path(str(video), base) != subtitle_tool.asr_cache_path(str(video), lang_changed)


def test_parse_srt_input_subtitle(tmp_path: Path):
    srt = tmp_path / "lesson.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:03,000\nhello\n", encoding="utf-8")

    result = subtitle_tool.parse_subtitle(str(srt))

    assert result["success"] is True
    assert result["backend"] == "srt_parser"
    assert result["data"]["segments"][0]["text"] == "hello"


def test_no_embedded_subtitle_stream_returns_empty_for_video():
    streams = subtitle_tool.subtitle_streams("data/raw/91cb993b715d0bdec8bf0194b14aa56a.mp4")
    assert streams == []
