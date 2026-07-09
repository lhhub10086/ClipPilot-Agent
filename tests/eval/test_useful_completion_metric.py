from eval.aggregate_results import useful_completion_rate


def test_useful_completion_metric_uses_human_acceptable_only():
    rows = [
        {"human_decision": "acceptable"},
        {"human_decision": "needs_minor_edit"},
        {"human_decision": "unacceptable"},
    ]
    assert useful_completion_rate(rows) == 1 / 3


def test_useful_completion_pending_when_no_human_review():
    assert useful_completion_rate([{"human_decision": ""}]) is None
