from __future__ import annotations

from clip_pilot.harness.artifact_validator import ArtifactValidator


def test_planner_llm_call_is_required_in_trace(tmp_path):
    root = tmp_path
    (root / "final_review.mp4").write_bytes(b"x")
    trace = {"steps": [{"step_name": "intent_parse"}, {"step_name": "planner_llm_call", "output_summary": {"fallback_used": False, "fallback_reason": None}}]}
    assert any(step["step_name"] == "planner_llm_call" for step in trace["steps"])
