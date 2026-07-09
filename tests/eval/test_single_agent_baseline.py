from eval.baselines.single_agent_baseline import run_single_agent_baseline
from eval.schemas.eval_case_schema import EvalCase


def test_single_agent_baseline_uses_one_llm_call_when_transcript_valid():
    case = EvalCase(
        case_id="c1",
        category="good_vtt",
        video_path="x.mp4",
        subtitle_path="x.vtt",
        language="en",
        intent="review",
        expected_behavior="export_or_valid_block",
    )
    result = run_single_agent_baseline(case)
    assert result.system_name == "single_agent_baseline"
    assert result.llm_call_count == 1
