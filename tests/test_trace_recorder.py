import json

from clip_pilot.harness import TraceRecorder


def test_trace_recorder_saves_json(tmp_path):
    path = tmp_path / "trace.json"
    trace = TraceRecorder()
    trace.record({"step_name": "x", "tool_name": "t", "success": True, "input_summary": {}, "output_summary": {}, "output_path": "", "error": None, "duration_seconds": 0})
    trace.save(path)
    assert json.loads(path.read_text(encoding="utf-8"))["steps"][0]["step_name"] == "x"

