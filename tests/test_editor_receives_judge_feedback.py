from clip_pilot.agent.timeline_repair import apply_repair


def test_editor_repair_receives_judge_feedback():
    timeline = {"timeline_items": [{"segment_id": "segment_001", "source_start": 10, "source_end": 20, "duration": 10, "source_block_ids": ["block_1"]}]}
    judge = {"major_problems": [{"type": "weak_transition"}], "segment_feedback": [{"segment_id": "segment_001", "keep": True}], "repair_instruction": {"insert_bridges": [{"segment_id": "segment_001", "bridge_after": "Next, connect this idea."}]}}
    _, actions = apply_repair(timeline, judge)
    assert actions["received_major_problems"] == judge["major_problems"]
    assert actions["received_segment_feedback"] == judge["segment_feedback"]
    assert actions["inserted_bridges"]
