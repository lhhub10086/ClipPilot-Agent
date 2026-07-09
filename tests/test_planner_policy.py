from clip_pilot.agent.planner import extract_requested_count
from clip_pilot.schemas.task_schema import WorkflowTask, normalize_task_plan


def test_task_default_has_no_fixed_three_segments():
    task = WorkflowTask(video_path="v.mp4", subtitle_path="s.vtt", intent="make review video", out_dir="out")
    assert task.clip_count is None


def test_user_requested_count_is_constraint_not_forced():
    plan = normalize_task_plan({"segment_count_policy": {"target_segments": 3, "allow_less_than_target": True}})
    assert plan["segment_count_policy"]["target_segments"] == 3
    assert plan["segment_count_policy"]["allow_less_than_target"] is True
    assert plan["segment_count_policy"]["mode"] == "adaptive"


def test_extract_requested_count_chinese_intent():
    assert extract_requested_count("剪出3个适合复习的片段") == 3

