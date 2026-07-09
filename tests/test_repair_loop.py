from clip_pilot.agent.timeline_repair import apply_repair, judge_passed


def test_repair_loop_drop_segment_instruction():
    timeline = {
        "timeline_items": [
            {"segment_id": "segment_001", "bridge_before": None, "bridge_after": None},
            {"segment_id": "segment_002", "bridge_before": None, "bridge_after": None},
        ],
        "editing_strategy": {},
    }
    judge = {"repair_instruction": {"drop_segments": ["segment_002"], "insert_bridges": [{"segment_id": "segment_001", "bridge_after": "next idea"}]}}
    repaired, actions = apply_repair(timeline, judge)
    assert [item["segment_id"] for item in repaired["timeline_items"]] == ["segment_001"]
    assert repaired["timeline_items"][0]["bridge_after"] == "next idea"
    assert actions["timeline_changed"] is True


def test_judge_passed_requires_score_and_no_major_problems():
    assert judge_passed({"passed": True, "score": 0.8, "major_problems": []})
    assert not judge_passed({"passed": True, "score": 0.8, "major_problems": [{"type": "topic_jump"}]})
    assert not judge_passed({"passed": True, "score": 0.7, "major_problems": []})
