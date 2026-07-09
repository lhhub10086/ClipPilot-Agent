from pathlib import Path


def test_eval_report_contains_limitations_and_sample_size():
    report = Path("docs/evaluation_report.md").read_text(encoding="utf-8")
    assert "Human review status" in report
    assert "sample size is small" in report
    assert "does not yet prove" in report
