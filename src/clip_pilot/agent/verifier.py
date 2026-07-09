from __future__ import annotations

from clip_pilot.schemas.edit_plan_schema import validate_edit_plan
from clip_pilot.schemas.timeline_schema import validate_timeline


def verify_timeline(timeline: dict) -> list[str]:
    return validate_timeline(timeline)


def verify_edit_plan(edit_plan: dict) -> list[str]:
    return validate_edit_plan(edit_plan)


