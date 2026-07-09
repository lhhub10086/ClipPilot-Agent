from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable


def _decision(row: dict[str, str]) -> str:
    return (row.get("human_decision") or "").strip()


def useful_completion_rate(rows: Iterable[dict[str, str]]) -> float | None:
    rows = list(rows)
    decisions = [_decision(row) for row in rows]
    if not any(decisions):
        return None
    return sum(decision == "acceptable" for decision in decisions) / len(rows)


def acceptable_or_minor_rate(rows: Iterable[dict[str, str]]) -> float | None:
    rows = list(rows)
    decisions = [_decision(row) for row in rows]
    if not any(decisions):
        return None
    return sum(decision in {"acceptable", "needs_minor_edit"} for decision in decisions) / len(rows)


def false_acceptance_rate(rows: Iterable[dict[str, str]]) -> float | None:
    accepted_by_system = [row for row in rows if str(row.get("automated_validation_passed")).lower() == "true"]
    if not accepted_by_system:
        return None
    human_labeled = [row for row in accepted_by_system if _decision(row)]
    if not human_labeled:
        return None
    return sum(_decision(row) == "unacceptable" for row in human_labeled) / len(human_labeled)


def bad_output_rejection_recall(rows: Iterable[dict[str, str]]) -> float | None:
    unacceptable = [row for row in rows if _decision(row) == "unacceptable"]
    if not unacceptable:
        return None
    rejected = [row for row in unacceptable if str(row.get("automated_validation_passed")).lower() != "true"]
    return len(rejected) / len(unacceptable)


def summarize(results_csv: Path, output_csv: Path) -> list[dict[str, str]]:
    with results_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_system: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_system[row["system_name"]].append(row)
    summary = []
    for system, system_rows in sorted(by_system.items()):
        repair_cases = [row for row in system_rows if str(row.get("repair_triggered")).lower() == "true"]
        summary.append(
            {
                "system_name": system,
                "case_count": str(len(system_rows)),
                "useful_completion_rate": _fmt(useful_completion_rate(system_rows)),
                "acceptable_or_minor_rate": _fmt(acceptable_or_minor_rate(system_rows)),
                "false_acceptance_rate": _fmt(false_acceptance_rate(system_rows)),
                "bad_output_rejection_recall": _fmt(bad_output_rejection_recall(system_rows)),
                "export_allow_rate": _fmt(_mean_bool(system_rows, "video_export_allowed")),
                "automated_pass_rate": _fmt(_mean_bool(system_rows, "automated_validation_passed")),
                "avg_llm_call_count": _fmt(_mean_float(system_rows, "llm_call_count")),
                "avg_latency_seconds": _fmt(_mean_float(system_rows, "latency_seconds")),
                "repair_case_count": str(len(repair_cases)),
            }
        )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()) if summary else ["system_name"])
        writer.writeheader()
        writer.writerows(summary)
    return summary


def _mean_bool(rows: list[dict[str, str]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(str(row.get(key)).lower() == "true" for row in rows) / len(rows)


def _mean_float(rows: list[dict[str, str]], key: str) -> float:
    values = [float(row.get(key) or 0.0) for row in rows]
    return sum(values) / len(values) if values else 0.0


def _fmt(value: float | None) -> str:
    return "pending" if value is None else f"{value:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate ClipPilot-Agent evaluation results.")
    parser.add_argument("--results", default="eval/outputs/results.csv")
    parser.add_argument("--output", default="eval/outputs/summary.csv")
    args = parser.parse_args()
    summarize(Path(args.results), Path(args.output))
    print(f"Wrote eval summary to {args.output}")


if __name__ == "__main__":
    main()
