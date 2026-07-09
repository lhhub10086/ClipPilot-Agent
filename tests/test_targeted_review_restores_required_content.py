from clip_pilot.tools.coherence_gap_analyzer import analyze_coherence_gaps


def test_targeted_review_restores_required_content_signal():
    judge = {"passed": False, "score": 0.6, "major_problems": [{"location": "between segment_001 and segment_002", "problem": "missing learning method bridge", "repair_action": "expand_context"}]}
    timeline = {"timeline_items": [{"segment_id": "segment_001", "source_start": 0, "source_end": 20, "source_block_ids": ["b1"]}, {"segment_id": "segment_002", "source_start": 80, "source_end": 100, "source_block_ids": ["b2"]}]}
    blocks = [{"block_id": "bridge", "start": 30, "end": 45, "contains_unresolved_asr": True, "lexical_risk_level": "medium_risk", "bridge_importance": 0.6, "unresolved_sentence_ids": ["s_bad"], "summary": "学习方法提醒"}]
    report = analyze_coherence_gaps(judge_response=judge, editor_timeline=timeline, semantic_blocks=blocks)
    assert report["manual_review_can_recover_coherence"] is True
    assert report["required_manual_review_sentence_ids"] == ["s_bad"]
