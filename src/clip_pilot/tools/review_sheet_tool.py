from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


FIELDS = ["video_id", "clip_id", "start", "end", "title", "reason", "review_question", "clip_suggestion", "transcript_evidence", "reviewer_score", "accepted", "comment"]


def write_review_sheet(video_id: str, clips: list[dict[str, Any]], output_path: str) -> dict[str, Any]:
    path = Path(output_path)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for clip in clips:
            writer.writerow({field: clip.get(field, "") for field in FIELDS} | {"video_id": video_id, "reviewer_score": "", "accepted": "", "comment": ""})
    return {"success": True, "backend": "csv_review_sheet", "output_path": str(path), "data": {"row_count": len(clips)}}

