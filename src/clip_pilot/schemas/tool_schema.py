from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    output_path: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


