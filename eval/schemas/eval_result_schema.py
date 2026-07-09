from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


HUMAN_FIELDS = [
    "human_task_completion_score",
    "human_coherence_score",
    "human_sentence_integrity_score",
    "human_content_value_score",
    "human_subtitle_accuracy_score",
    "human_rough_cut_usability_score",
    "human_overall_score",
    "human_decision",
]


@dataclass
class EvalResult:
    case_id: str
    system_name: str
    category: str
    language: str
    transcript_source: str = "unknown"
    transcript_valid: bool = False
    selected_scope_lexical_valid: bool = False
    judge_initial_score: float | None = None
    judge_final_score: float | None = None
    repair_triggered: bool = False
    repair_rounds: int = 0
    task_coverage_score: float | None = None
    task_coverage_valid: bool = False
    content_sufficiency_valid: bool = False
    policy_valid: bool = False
    media_valid: bool = False
    video_export_allowed: bool = False
    video_exported: bool = False
    automated_validation_passed: bool = False
    blocked_reason: str | None = None
    segment_count: int = 0
    final_duration_seconds: float = 0.0
    llm_call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    latency_seconds: float = 0.0
    human_task_completion_score: str = ""
    human_coherence_score: str = ""
    human_sentence_integrity_score: str = ""
    human_content_value_score: str = ""
    human_subtitle_accuracy_score: str = ""
    human_rough_cut_usability_score: str = ""
    human_overall_score: str = ""
    human_decision: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
