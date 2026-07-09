from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationReport:
    success: bool
    checks: dict[str, bool]
    error: str | None = None

