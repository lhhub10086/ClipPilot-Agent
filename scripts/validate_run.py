from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FILES = [
    "validation_report.json",
    "workflow_summary.json",
    "trace.json",
]


def validate_run(run_dir: str) -> dict:
    root = Path(run_dir)
    missing = [name for name in REQUIRED_FILES if not (root / name).exists()]
    validation = {}
    if (root / "validation_report.json").exists():
        validation = json.loads((root / "validation_report.json").read_text(encoding="utf-8"))
    summary = {}
    if (root / "workflow_summary.json").exists():
        summary = json.loads((root / "workflow_summary.json").read_text(encoding="utf-8"))
    return {
        "run_dir": str(root),
        "missing_required_files": missing,
        "run_completed": validation.get("run_completed"),
        "automated_validation_passed": validation.get("automated_validation_passed"),
        "human_review_status": validation.get("human_review_status") or summary.get("human_review_status"),
        "production_ready": validation.get("production_ready") or summary.get("production_ready"),
        "blocked_or_failed_reason": validation.get("blocked_reason") or validation.get("failed_reason") or summary.get("failed_reason"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a ClipPilot-Agent run directory without re-running the workflow.")
    parser.add_argument("--run-dir", required=True, help="Path to an outputs/<run_id> directory.")
    args = parser.parse_args()
    print(json.dumps(validate_run(args.run_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

