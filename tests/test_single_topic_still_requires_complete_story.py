from clip_pilot.tools.task_coverage_validator import build_task_coverage_report


def test_single_topic_still_requires_complete_story_roles():
    timeline = {"timeline_items": [{"segment_id": "s1", "role": "introduction", "duration": 30, "transcript": "今天讲初高中物理的区别。"}]}
    report = build_task_coverage_report(user_intent="初高中物理衔接第一课复习", task_plan={}, editor_timeline=timeline)
    assert report["narrative_roles"]["introduction"] is True
    assert report["narrative_roles"]["closing_or_summary"] is False
    assert report["content_sufficiency_valid"] is False
