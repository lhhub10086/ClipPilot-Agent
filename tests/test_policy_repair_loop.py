from pathlib import Path

from clip_pilot.agent.timeline_repair import run_timeline_repair_round


def test_policy_repair_reduces_scope_and_removes_reused_bridges(tmp_path: Path):
    semantic_blocks = [
        {"block_id": f"block_{idx:04}", "start": idx * 10.0, "end": idx * 10.0 + 10.0, "text": f"Block {idx} explanation."}
        for idx in range(30)
    ]
    timeline = {
        "timeline_items": [
            {
                "segment_id": "segment_001",
                "source_block_ids": [block["block_id"] for block in semantic_blocks],
                "source_start": 0.0,
                "source_end": 300.0,
                "duration": 300.0,
                "bridge_after": "old bridge",
            }
        ]
    }
    task_plan = {
        "segment_count_policy": {"min_segments": 1, "max_segments": 20, "target_segments": 12, "allow_less_than_target": True},
        "duration_policy": {"max_final_duration_seconds": 240, "max_segment_seconds": 18},
    }
    policy_report = {"policy_valid": False, "violations": [{"type": "final_duration_exceeds_policy", "severity": "blocking"}]}
    judge = {"passed": True, "score": 0.95, "major_problems": []}

    result = run_timeline_repair_round(
        editor_timeline=timeline,
        judge_response=judge,
        output_dir=str(tmp_path),
        round_index=1,
        policy_report=policy_report,
        task_plan=task_plan,
        semantic_blocks=semantic_blocks,
    )

    items = result["data"]["editor_timeline"]["timeline_items"]
    assert 1 <= len(items) <= 12
    assert sum(float(item["duration"]) for item in items) <= 245
    assert all(float(item["duration"]) <= 23 for item in items)
    assert all(item.get("bridge_after") is None for item in items)
