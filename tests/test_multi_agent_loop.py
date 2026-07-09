from clip_pilot.schemas.trace_schema import REQUIRED_TRACE_STEPS


def test_required_trace_steps_include_multi_agent_loop():
    for step in [
        "selector_llm_call",
        "editor_llm_call",
        "final_review_transcript_generation",
        "judge_llm_call",
        "timeline_repair_loop",
        "export_gate_decision",
    ]:
        assert step in REQUIRED_TRACE_STEPS
