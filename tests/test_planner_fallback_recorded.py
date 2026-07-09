from __future__ import annotations

from clip_pilot.agent.planner import build_task_plan


def test_planner_fallback_is_explicit_when_llm_disabled(tmp_path):
    plan = build_task_plan(
        intent="从这段40分钟课程视频中生成一个适合学生快速复习的高光粗剪版本，保留关键知识点，节奏紧凑，不需要固定片段数量。",
        video_metadata={"video_path": "demo.mp4"},
        subtitle_metadata={"duration": 2400, "segment_count": 100},
        config={"llm": {"model": "deepseek-chat"}},
        output_dir=str(tmp_path),
        no_llm_planner=True,
    )
    assert plan["planner_fallback_used"] is True
    assert plan["planner_fallback_reason"]
    assert (tmp_path / "planner_raw_response.json").exists()
    assert (tmp_path / "task_plan.json").exists()
    assert plan["task_type"] == "highlight_reel"
