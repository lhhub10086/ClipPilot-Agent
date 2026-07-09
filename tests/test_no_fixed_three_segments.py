from clip_pilot.schemas.task_schema import normalize_task_plan


def test_no_target_when_user_does_not_specify_count():
    plan = normalize_task_plan({})
    assert plan["segment_count_policy"]["target_segments"] is None
    assert plan["segment_count_policy"]["mode"] == "adaptive"

