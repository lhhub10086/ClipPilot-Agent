from clip_pilot.harness import ToolRegistry


def test_tool_registry_registers_and_gets_tool():
    registry = ToolRegistry()
    registry.register("x", lambda: {"success": True})
    assert registry.get("x")()["success"] is True
    assert registry.names() == ["x"]

