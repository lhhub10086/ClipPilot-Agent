from __future__ import annotations

from clip_pilot.agent.planner import detect_task_type, load_policy_defaults


def test_highlight_reel_policy_has_micro_clip_defaults():
    intent = "从这段40分钟课程视频中生成一个适合学生快速复习的高光粗剪版本，节奏紧凑，不需要固定片段数量。"
    task_type = detect_task_type(intent)
    policy = load_policy_defaults(task_type)
    assert task_type == "highlight_reel"
    assert policy["segment_count_policy"]["target_segments"] != 3
    assert policy["segment_count_policy"]["min_segments"] >= 8
    assert policy["duration_policy"]["min_segment_seconds"] == 6
    assert policy["duration_policy"]["max_segment_seconds"] == 18
