from clip_pilot.tools.task_coverage_validator import build_task_coverage_report


def test_task_coverage_validator_requires_core_goals():
    timeline = {
        "timeline_items": [
            {"segment_id": "s1", "role": "hook", "duration": 20, "transcript": "初中物理和高中物理有什么区别和联系？高中物理要学什么？"}
        ]
    }
    report = build_task_coverage_report(user_intent="初高中物理衔接课后快速复习", task_plan={}, editor_timeline=timeline)
    assert report["task_coverage_valid"] is False
    assert report["content_sufficiency_valid"] is False
    assert report["degenerate_output"] is True
