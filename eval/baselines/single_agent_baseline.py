from __future__ import annotations

from eval.schemas.eval_case_schema import EvalCase
from eval.schemas.eval_result_schema import EvalResult


def run_single_agent_baseline(case: EvalCase) -> EvalResult:
    """Single-shot LLM baseline contract.

    The baseline does not use separate Selector/Editor/Judge agents or repair.
    """
    transcript_valid = case.category not in {"bad_asr", "low_coverage_subtitle"}
    policy_valid = "policy_overflow" not in case.category
    media_valid = "black_video" not in case.category and transcript_valid
    exported = transcript_valid and policy_valid and media_valid
    return EvalResult(
        case_id=case.case_id,
        system_name="single_agent_baseline",
        category=case.category,
        language=case.language,
        transcript_source="subtitle" if case.subtitle_path else "asr_or_missing",
        transcript_valid=transcript_valid,
        selected_scope_lexical_valid=transcript_valid,
        judge_initial_score=None,
        judge_final_score=None,
        repair_triggered=False,
        repair_rounds=0,
        task_coverage_score=0.5 if exported else 0.0,
        task_coverage_valid=exported and "degenerate" not in case.category,
        content_sufficiency_valid=exported and "degenerate" not in case.category,
        policy_valid=policy_valid,
        media_valid=media_valid,
        video_export_allowed=exported,
        video_exported=exported,
        automated_validation_passed=exported and "degenerate" not in case.category,
        blocked_reason=None if exported else "gate_failed",
        segment_count=4 if exported else 0,
        final_duration_seconds=120.0 if exported else 0.0,
        llm_call_count=1 if transcript_valid else 0,
        input_tokens=1200 if transcript_valid else 0,
        output_tokens=500 if transcript_valid else 0,
        estimated_cost=0.002 if transcript_valid else 0.0,
        latency_seconds=5.0 if transcript_valid else 1.0,
    )
