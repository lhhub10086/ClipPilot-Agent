from clip_pilot.tools.task_coverage_validator import build_task_coverage_report


def test_single_segment_degenerate_output_even_with_clear_intro():
    timeline = {"timeline_items": [{"segment_id": "s1", "role": "core_concept", "duration": 20, "transcript": "第一个问题，初中物理和高中物理的区别和联系。"}]}
    report = build_task_coverage_report(user_intent="课后快速复习粗剪", task_plan={}, editor_timeline=timeline)
    assert report["degenerate_output"] is True
    assert "single_segment_only" in report["degenerate_reasons"]
    assert "too_short_for_review_task" in report["degenerate_reasons"]
