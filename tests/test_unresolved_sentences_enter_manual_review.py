import csv
from pathlib import Path


def test_unresolved_sentences_enter_manual_review(tmp_path: Path):
    path = tmp_path / "subtitle_manual_review.csv"
    rows = [
        {
            "sentence_id": "s1",
            "start": "1.0",
            "end": "2.0",
            "audio_clip_path": "a.wav",
            "context_before": "",
            "original_text": "信奥义",
            "candidate_text": "信奥义",
            "context_after": "",
            "confidence": "0.0",
            "risk_types": "semantic_anomaly",
            "review_status": "pending",
        }
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    loaded = list(csv.DictReader(path.open(encoding="utf-8")))
    assert loaded[0]["review_status"] == "pending"
    assert loaded[0]["sentence_id"] == "s1"
