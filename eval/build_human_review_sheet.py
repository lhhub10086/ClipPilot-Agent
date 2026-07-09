from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.schemas.human_review_schema import HUMAN_REVIEW_FIELDS


def build_sheet(raw_results_path: Path, output_path: Path, seed: int = 2026) -> None:
    rows = []
    for line in raw_results_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        result = json.loads(line)
        output_id = hashlib.sha1(f"{result['case_id']}::{result['system_name']}".encode("utf-8")).hexdigest()[:12]
        rows.append(
            {
                "output_id": output_id,
                "case_id": result["case_id"],
                "category": result["category"],
                "language": result["language"],
                "intent": "",
                "artifact_dir": "",
                "task_completion_score": "",
                "coherence_score": "",
                "sentence_integrity_score": "",
                "content_value_score": "",
                "subtitle_accuracy_score": "",
                "rough_cut_usability_score": "",
                "overall_score": "",
                "decision": "",
                "comments": "",
            }
        )
    random.Random(seed).shuffle(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HUMAN_REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a blinded human review sheet from eval raw results.")
    parser.add_argument("--raw-results", default="eval/outputs/raw_results.jsonl")
    parser.add_argument("--output", default="eval/outputs/human_review_sheet.csv")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    build_sheet(Path(args.raw_results), Path(args.output), args.seed)
    print(f"Wrote blinded human review sheet to {args.output}")


if __name__ == "__main__":
    main()
