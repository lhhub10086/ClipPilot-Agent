from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., dict[str, Any]]] = {}

    def register(self, name: str, func: Callable[..., dict[str, Any]]) -> None:
        if not name:
            raise ValueError("tool name cannot be empty")
        self._tools[name] = func

    def get(self, name: str) -> Callable[..., dict[str, Any]]:
        if name not in self._tools:
            raise KeyError(f"tool not registered: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)


