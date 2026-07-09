from __future__ import annotations

from clip_pilot.agent.planner import load_policy_defaults
from clip_pilot.tools.candidate_tool import generate_candidates


def test_highlight_reel_generates_micro_clip_candidates():
    segments = [
        {"start": i * 3.0, "end": i * 3.0 + 3.0, "text": "This method explains an important definition and example for learning."}
        for i in range(30)
    ]
    policy = load_policy_defaults("highlight_reel")
    result = generate_candidates(segments, policy)
    candidates = result["data"]["candidates"]
    assert candidates
    assert all(6.0 <= item["duration"] <= 18.0 for item in candidates)
    assert {"transcript_token_count", "semantic_boundary_score", "density_score", "keyword_score", "cut_quality_score"}.issubset(candidates[0])
