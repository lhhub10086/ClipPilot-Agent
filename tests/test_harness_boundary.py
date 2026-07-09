from clip_pilot.harness import RunContext


def test_harness_context_does_not_force_segment_count():
    ctx = RunContext(video_path="v.mp4", subtitle_path="s.vtt", intent="make review video", out_dir="out")
    assert ctx.clip_count is None
