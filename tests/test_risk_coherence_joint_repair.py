from clip_pilot.agent.risk_coherence_repair import repair_timeline


def test_risk_coherence_joint_repair_uses_safe_replacement():
    timeline = {"timeline_items": [{"segment_id": "segment_001", "source_block_ids": ["old"], "source_start": 0, "source_end": 10}]}
    blocks = [
        {"block_id": "old", "start": 0, "end": 10, "text": "old", "lexical_risk_level": "low_risk"},
        {"block_id": "safe", "start": 12, "end": 20, "text": "safe", "lexical_risk_level": "low_risk", "narrative_importance": 0.9},
    ]
    gap = {"gaps": [{"recommended_action": "safe_replacement", "between": ["segment_001"], "safe_alternative_candidates": [{"block_id": "safe"}]}]}
    repaired, actions = repair_timeline(timeline, gap, blocks)
    assert actions["safe_replacements"]
    assert repaired["timeline_items"][0]["source_block_ids"] == ["safe"]
