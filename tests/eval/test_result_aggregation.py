import csv

from eval.aggregate_results import summarize


def test_result_aggregation_writes_summary(tmp_path):
    results = tmp_path / "results.csv"
    with results.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "system_name",
                "automated_validation_passed",
                "video_export_allowed",
                "llm_call_count",
                "latency_seconds",
                "repair_triggered",
                "human_decision",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "system_name": "multi_agent_harness",
                "automated_validation_passed": "True",
                "video_export_allowed": "True",
                "llm_call_count": "4",
                "latency_seconds": "10",
                "repair_triggered": "False",
                "human_decision": "",
            }
        )
    summary = summarize(results, tmp_path / "summary.csv")
    assert summary[0]["useful_completion_rate"] == "pending"
    assert (tmp_path / "summary.csv").exists()
