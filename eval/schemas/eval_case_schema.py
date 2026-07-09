from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    category: str
    video_path: str
    subtitle_path: str | None
    language: str
    intent: str
    expected_behavior: str
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalCase":
        required = ["case_id", "category", "video_path", "language", "intent", "expected_behavior"]
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"Eval case missing required fields: {missing}")
        return cls(
            case_id=str(data["case_id"]),
            category=str(data["category"]),
            video_path=str(data["video_path"]),
            subtitle_path=data.get("subtitle_path"),
            language=str(data["language"]),
            intent=str(data["intent"]),
            expected_behavior=str(data["expected_behavior"]),
            notes=str(data.get("notes", "")),
        )

    def resolved_video_path(self) -> Path:
        return Path(os.path.expandvars(self.video_path))

    def resolved_subtitle_path(self) -> Path | None:
        if not self.subtitle_path:
            return None
        return Path(os.path.expandvars(self.subtitle_path))
