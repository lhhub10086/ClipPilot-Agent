from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clip_pilot.tools.subtitle_refinement_tool import to_vtt, write_srt


def apply_review(
    *,
    review_csv: str,
    sentence_units_path: str,
    semantic_blocks_path: str,
    output_dir: str,
) -> dict:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    units_payload = json.loads(Path(sentence_units_path).read_text(encoding="utf-8"))
    blocks_payload = json.loads(Path(semantic_blocks_path).read_text(encoding="utf-8"))
    units = units_payload.get("sentence_units", [])
    blocks = blocks_payload.get("semantic_blocks", [])
    corrections = _load_approved_corrections(review_csv)
    before_after = []
    for unit in units:
        sid = str(unit.get("sentence_id"))
        if sid not in corrections:
            continue
        old_text = unit.get("refined_text") or unit.get("text") or ""
        new_text = corrections[sid]
        unit["refined_text"] = new_text
        unit["text"] = new_text
        unit.setdefault("review", {})["status"] = "approved"
        before_after.append({"sentence_id": sid, "before": old_text, "after": new_text, "start": unit.get("start"), "end": unit.get("end"), "source_cue_ids": unit.get("source_cue_ids", [])})

    unit_by_id = {unit["sentence_id"]: unit for unit in units}
    for block in blocks:
        texts = []
        for sid in block.get("sentence_ids", []):
            unit = unit_by_id.get(sid)
            if unit:
                texts.append(unit.get("refined_text") or unit.get("text") or "")
        if texts:
            block["text"] = "".join(texts)
            block["summary"] = block["text"][:120]

    reviewed_units_path = root / "sentence_units_reviewed.json"
    reviewed_blocks_path = root / "semantic_blocks_reviewed.json"
    reviewed_srt_path = root / "refined_subtitle_reviewed.srt"
    reviewed_vtt_path = root / "refined_subtitle_reviewed.vtt"
    diff_path = root / "subtitle_review_diff.json"
    reviewed_units_path.write_text(json.dumps({"sentence_units": units}, ensure_ascii=False, indent=2), encoding="utf-8")
    reviewed_blocks_path.write_text(json.dumps({"semantic_blocks": blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
    subtitle_rows = [{"start": unit["start"], "end": unit["end"], "text": unit.get("refined_text", "")} for unit in units]
    write_srt(subtitle_rows, reviewed_srt_path)
    reviewed_vtt_path.write_text(to_vtt(subtitle_rows), encoding="utf-8")
    diff_path.write_text(json.dumps({"changed_count": len(before_after), "changes": before_after}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "changed_count": len(before_after),
        "sentence_units_reviewed": str(reviewed_units_path),
        "semantic_blocks_reviewed": str(reviewed_blocks_path),
        "refined_subtitle_reviewed_srt": str(reviewed_srt_path),
        "refined_subtitle_reviewed_vtt": str(reviewed_vtt_path),
        "diff_path": str(diff_path),
    }


def _load_approved_corrections(review_csv: str) -> dict[str, str]:
    corrections: dict[str, str] = {}
    with Path(review_csv).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if str(row.get("review_status", "")).strip().lower() != "approved":
                continue
            corrected = str(row.get("corrected_text", "")).strip()
            sid = str(row.get("sentence_id", "")).strip()
            if sid and corrected:
                corrections[sid] = corrected
    return corrections


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply approved subtitle manual review corrections.")
    parser.add_argument("--review-csv", required=True)
    parser.add_argument("--sentence-units", required=True)
    parser.add_argument("--semantic-blocks", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(apply_review(review_csv=args.review_csv, sentence_units_path=args.sentence_units, semantic_blocks_path=args.semantic_blocks, output_dir=args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

