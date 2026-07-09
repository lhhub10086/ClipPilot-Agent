from clip_pilot.tools.transcript_quality_tool import build_quality_report


def test_garbled_asr_cache_transcript_is_invalid():
    segments = [
        {"start": 0.0, "end": 4.0, "text": "鐪熺殑 鎴戜笉绲﹀ぇ瀹惰瑳"},
        {"start": 10.0, "end": 13.0, "text": "閭ｉ杭浠婂ぉ 涓€鍊嬪晱椤"},
    ]
    report = build_quality_report(segments=segments, video_duration=120.0, backend="vtt_parser_asr_cache")
    assert report["transcript_valid"] is False
    assert "garbled_text" in report["major_issues"] or "asr_cache_low_coverage" in report["major_issues"]


def test_clean_english_vtt_transcript_is_valid():
    segments = [
        {"start": 0.0, "end": 8.0, "text": "Modern CPUs use caches to reduce memory latency."},
        {"start": 8.0, "end": 16.0, "text": "Instruction pipelining overlaps fetch, decode, and execute stages."},
        {"start": 16.0, "end": 24.0, "text": "Branch prediction helps avoid pipeline stalls."},
        {"start": 24.0, "end": 32.0, "text": "Multi-core processors run multiple instruction streams."},
        {"start": 32.0, "end": 40.0, "text": "These techniques improve throughput in different ways."},
    ]
    report = build_quality_report(segments=segments, video_duration=42.0, backend="vtt_parser", subtitle_path="demo.vtt")
    assert report["transcript_valid"] is True
    assert report["transcript_source"] == "provided_vtt"
