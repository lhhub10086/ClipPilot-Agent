from eval.aggregate_results import false_acceptance_rate, useful_completion_rate


def test_no_output_system_cannot_be_called_best_from_false_acceptance_alone():
    rows = [{"automated_validation_passed": "False", "human_decision": ""}]
    assert false_acceptance_rate(rows) is None
    assert useful_completion_rate(rows) is None
