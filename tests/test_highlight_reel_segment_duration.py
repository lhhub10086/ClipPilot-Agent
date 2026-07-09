from __future__ import annotations

from clip_pilot.agent.planner import load_policy_defaults
from clip_pilot.tools.candidate_tool import generate_candidates, select_candidates


def test_highlight_reel_selected_segments_are_short():
    segments = [
        {"start": i * 3.0, "end": i * 3.0 + 3.0, "text": "Important algorithm method example definition for student review."}
        for i in range(60)
    ]
    policy = load_policy_defaults("highlight_reel")
    candidates = generate_candidates(segments, policy)["data"]["candidates"]
    selected = select_candidates(candidates, policy)["data"]["selected"]
    assert selected
    assert all(6.0 <= item["duration"] <= 18.0 for item in selected)
    assert sum(item["duration"] for item in selected) <= policy["duration_policy"]["max_final_duration_seconds"]
