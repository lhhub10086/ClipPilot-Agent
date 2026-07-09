from clip_pilot.tools.transcript_quality_tool import build_quality_report


def test_timing_quality_flags_fragmented_subtitles():
    segments = [{"start": i * 1.0, "end": i * 1.0 + 1.0, "text": "短句"} for i in range(10)]
    report = build_quality_report(segments=segments, video_duration=10.0, backend="faster_whisper")

    assert report["short_cue_ratio"] == 1.0
    assert "subtitle_segments_too_fragmented" in report["major_issues"]
