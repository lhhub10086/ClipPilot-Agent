from eval.baselines.rule_baseline import run_rule_baseline
from eval.schemas.eval_case_schema import EvalCase


def test_rule_baseline_does_not_call_llm():
    case = EvalCase(
        case_id="c1",
        category="good_vtt",
        video_path="x.mp4",
        subtitle_path="x.vtt",
        language="en",
        intent="review",
        expected_behavior="export_or_valid_block",
    )
    result = run_rule_baseline(case)
    assert result.system_name == "rule_baseline"
    assert result.llm_call_count == 0
