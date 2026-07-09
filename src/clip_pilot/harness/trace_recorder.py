from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TraceRecorder:
    def __init__(self) -> None:
        self.steps: list[dict[str, Any]] = []

    def record(self, event: dict[str, Any]) -> None:
        self.steps.append(event)

    def to_dict(self) -> dict[str, Any]:
        return {"steps": self.steps}

    def save(self, path: str | Path) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return str(target)


