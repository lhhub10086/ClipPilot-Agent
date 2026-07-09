from eval.aggregate_results import false_acceptance_rate


def test_false_acceptance_metric_counts_unacceptable_system_passes():
    rows = [
        {"automated_validation_passed": "True", "human_decision": "unacceptable"},
        {"automated_validation_passed": "True", "human_decision": "acceptable"},
        {"automated_validation_passed": "False", "human_decision": "unacceptable"},
    ]
    assert false_acceptance_rate(rows) == 0.5


def test_false_acceptance_pending_without_human_review():
    rows = [{"automated_validation_passed": "True", "human_decision": ""}]
    assert false_acceptance_rate(rows) is None
