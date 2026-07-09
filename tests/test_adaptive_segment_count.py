from clip_pilot.tools.candidate_tool import select_candidates


def test_policy_allows_less_than_target_when_quality_low():
    candidates = [
        {"candidate_id": "a", "start": 0, "end": 30, "duration": 30, "cut_quality_score": 0.8, "score": 0.8, "transcript": "a"},
        {"candidate_id": "b", "start": 40, "end": 70, "duration": 30, "cut_quality_score": 0.4, "score": 0.4, "transcript": "b"},
    ]
    policy = {
        "segment_count_policy": {"max_segments": 3, "target_segments": 3, "allow_less_than_target": True},
        "duration_policy": {"max_final_duration_seconds": 180},
        "selection_policy": {"min_cut_quality_score": 0.6},
    }
    result = select_candidates(candidates, policy)
    assert result["data"]["selected_count"] == 1

