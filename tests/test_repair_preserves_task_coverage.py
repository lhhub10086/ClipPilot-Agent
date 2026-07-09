from clip_pilot.agent.risk_coherence_repair import assess_repair_tradeoff


def test_repair_preserves_task_coverage():
    before_cov = {"coverage_score": 0.8, "degenerate_output": False}
    after_cov = {"coverage_score": 0.35, "degenerate_output": True}
    before_timeline = {"timeline_items": [{"duration": 80}, {"duration": 70}, {"duration": 50}]}
    after_timeline = {"timeline_items": [{"duration": 20}]}
    decision = assess_repair_tradeoff(before_cov, after_cov, before_timeline, after_timeline)
    assert decision["repair_accepted"] is False
    assert decision["degenerate_output_detected"] is True
