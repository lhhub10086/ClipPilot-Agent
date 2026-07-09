from clip_pilot.harness import StepExecutor, TraceRecorder


def test_step_executor_records_success():
    trace = TraceRecorder()
    result = StepExecutor(trace).run(step_name="s", tool_name="t", input_summary={}, func=lambda: {"success": True, "data": {"selected_count": 1}})
    assert result["success"] is True
    assert trace.steps[0]["step_name"] == "s"

