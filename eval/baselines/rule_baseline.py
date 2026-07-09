from __future__ import annotations

from eval.schemas.eval_case_schema import EvalCase
from eval.schemas.eval_result_schema import EvalResult


def run_rule_baseline(case: EvalCase) -> EvalResult:
    """Deterministic lightweight baseline placeholder.

    It models the rule pipeline contract without claiming content quality.
    Real clip export can be wired in later; human fields remain blank.
    """
    transcript_valid = case.category not in {"bad_asr", "low_coverage_subtitle"}
    exported = transcript_valid and "media_broken" not in case.category
    return EvalResult(
        case_id=case.case_id,
        system_name="rule_baseline",
        category=case.category,
        language=case.language,
        transcript_source="subtitle" if case.subtitle_path else "asr_or_missing",
        transcript_valid=transcript_valid,
        selected_scope_lexical_valid=transcript_valid,
        task_coverage_score=0.35 if exported else 0.0,
        task_coverage_valid=False,
        content_sufficiency_valid=False,
        policy_valid=exported,
        media_valid=exported,
        video_export_allowed=exported,
        video_exported=exported,
        automated_validation_passed=False,
        blocked_reason=None if exported else "transcript_or_media_failed",
        segment_count=3 if exported else 0,
        final_duration_seconds=90.0 if exported else 0.0,
        llm_call_count=0,
        latency_seconds=1.0,
    )
