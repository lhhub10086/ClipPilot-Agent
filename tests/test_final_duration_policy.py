from clip_pilot.tools.policy_validator import build_policy_report


def test_final_duration_within_policy_passes():
    task_plan = {
        "segment_count_policy": {"min_segments": 1, "max_segments": 20, "allow_less_than_target": True},
        "duration_policy": {"max_final_duration_seconds": 240, "max_segment_seconds": 130},
    }
    timeline = {"timeline_items": [{"segment_id": "a", "duration": 120.0}, {"segment_id": "b", "duration": 60.0}]}

    report = build_policy_report(task_plan=task_plan, editor_timeline=timeline)

    assert report["policy_valid"] is True
    assert report["final_duration_seconds"] == 180.0
