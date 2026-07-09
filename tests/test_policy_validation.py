from clip_pilot.harness.artifact_validator import _segment_count_matches_policy


def test_validation_allows_less_than_target_when_policy_allows():
    timeline = {"items": [{"item_id": "segment_001"}]}
    policy = {"segment_count_policy": {"min_segments": 1, "max_segments": 5, "target_segments": 3, "allow_less_than_target": True}}
    assert _segment_count_matches_policy(timeline, policy) is True

