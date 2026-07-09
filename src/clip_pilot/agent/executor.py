from __future__ import annotations

from clip_pilot.workflows.content_review_workflow import run_content_review_workflow


def run_agent_workflow(**kwargs):
    return run_content_review_workflow(**kwargs)


