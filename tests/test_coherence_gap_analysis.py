from clip_pilot.tools.coherence_gap_analyzer import analyze_coherence_gaps


def test_coherence_gap_analysis_finds_nearby_risky_bridge(tmp_path):
    judge = {"passed": False, "score": 0.5, "major_problems": [{"type": "topic_jump", "location": "between segment_001 and segment_002", "problem": "missing bridge", "repair_action": "expand_context"}]}
    timeline = {"timeline_items": [{"segment_id": "segment_001", "source_start": 0, "source_end": 20, "source_block_ids": ["safe1"]}, {"segment_id": "segment_002", "source_start": 60, "source_end": 80, "source_block_ids": ["safe2"]}]}
    blocks = [{"block_id": "bridge", "start": 25, "end": 35, "contains_unresolved_asr": True, "lexical_risk_level": "medium_risk", "bridge_importance": 0.5, "unresolved_sentence_ids": ["s1"], "summary": "bridge"}]
    report = analyze_coherence_gaps(judge_response=judge, editor_timeline=timeline, semantic_blocks=blocks, output_path=str(tmp_path / "gap.json"))
    assert report["gap_count"] == 1
    assert report["gaps"][0]["excluded_candidates_near_gap"][0]["block_id"] == "bridge"
    assert report["manual_review_can_recover_coherence"] is True
