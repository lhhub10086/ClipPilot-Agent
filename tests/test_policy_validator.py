from pathlib import Path

from clip_pilot.tools.policy_validator import build_policy_report


def _task_plan(max_final=240, max_segment=18, max_segments=20):
    return {
        "task_type": "highlight_reel",
        "segment_count_policy": {"min_segments": 1, "max_segments": max_segments, "target_segments": 12, "allow_less_than_target": True},
        "duration_policy": {"max_final_duration_seconds": max_final, "max_segment_seconds": max_segment},
    }


def test_policy_validator_rejects_final_duration_over_budget(tmp_path: Path):
    transcript = tmp_path / "final_review_transcript.md"
    transcript.write_text("short transcript", encoding="utf-8")
    timeline = {"timeline_items": [{"segment_id": "s1", "duration": 619.417}]}

    report = build_policy_report(task_plan=_task_plan(), editor_timeline=timeline, transcript_markdown_path=str(transcript))

    assert report["policy_valid"] is False
    assert any(item["type"] == "final_duration_exceeds_policy" for item in report["violations"])
    assert any(item["type"] == "no_policy_overflow" for item in report["violations"])


def test_policy_validator_rejects_segment_duration_over_budget(tmp_path: Path):
    transcript = tmp_path / "final_review_transcript.md"
    transcript.write_text("short transcript", encoding="utf-8")
    timeline = {"timeline_items": [{"segment_id": "s1", "duration": 45.0}]}

    report = build_policy_report(task_plan=_task_plan(max_final=240, max_segment=18), editor_timeline=timeline, transcript_markdown_path=str(transcript))

    assert report["policy_valid"] is False
    assert any(item["type"] == "segment_duration_exceeds_policy" for item in report["violations"])
