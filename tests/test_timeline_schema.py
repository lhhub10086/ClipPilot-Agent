import json
from pathlib import Path

from clip_pilot.schemas import validate_timeline


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "bad_transcript_run"


def test_timeline_schema_and_assets():
    if not (OUT / "timeline.json").exists():
        report = json.loads((OUT / "validation_report.json").read_text(encoding="utf-8"))
        if not report["transcript_valid"]:
            assert report["blocked_reason"] == "transcript_quality_failed"
            return
        semantic = json.loads((OUT / "semantic_timeline.json").read_text(encoding="utf-8"))
        gate = json.loads((OUT / "export_gate_decision.json").read_text(encoding="utf-8"))
        if not gate["video_export_allowed"]:
            assert semantic["items"] == []
            return
        assert semantic["items"]
        for item in semantic["items"]:
            assert item["source_start"] < item["source_end"]
            assert item["starts_mid_sentence"] is False
        return
    timeline = json.loads((OUT / "timeline.json").read_text(encoding="utf-8"))
    assert validate_timeline(timeline) == []
    for item in timeline["items"]:
        assert item["source_start"] < item["source_end"]
        assert item["target_start"] < item["target_end"]
        assert (OUT / item["asset_path"]).exists()
