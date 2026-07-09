from clip_pilot.harness import RunContext


def test_run_context_prepares_output_dirs(tmp_path):
    ctx = RunContext(video_path="a.mp4", subtitle_path="a.vtt", intent="intent", out_dir=str(tmp_path))
    ctx.prepare_dirs()
    assert ctx.selected_segments_dir.exists()
    assert ctx.title_cards_dir.exists()
    assert ctx.temp_chunks_dir.exists()

