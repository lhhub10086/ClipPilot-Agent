from eval.run_eval import load_cases, run_system


def test_eval_results_do_not_auto_fill_human_fields():
    case = load_cases(__import__("pathlib").Path("eval/cases.yaml"), limit=1)[0]
    result = run_system(case, "multi_agent_harness")
    assert result.human_decision == ""
    assert result.human_overall_score == ""
