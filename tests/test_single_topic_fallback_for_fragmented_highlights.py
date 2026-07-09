from clip_pilot.agent.risk_coherence_repair import repair_timeline


def test_single_topic_fallback_for_fragmented_highlights():
    timeline = {
        "timeline_items": [
            {"segment_id": "segment_001", "source_block_ids": ["b1"], "source_start": 0, "source_end": 10},
            {"segment_id": "segment_002", "source_block_ids": ["b2"], "source_start": 1000, "source_end": 1010},
        ]
    }
    blocks = [
        {"block_id": "b1", "start": 0, "end": 10, "text": "初中物理", "lexical_risk_level": "low_risk", "narrative_importance": 0.8},
        {"block_id": "b2", "start": 1000, "end": 1010, "text": "高中物理", "lexical_risk_level": "low_risk", "narrative_importance": 0.8},
    ]
    repaired, actions = repair_timeline(timeline, {"gaps": [{"recommended_action": "reduce_scope"}]}, blocks)
    assert actions["reduced_scope"] is True
    assert len(repaired["timeline_items"]) == 1
    assert repaired["editing_strategy"]["mode"] == "single_topic"
