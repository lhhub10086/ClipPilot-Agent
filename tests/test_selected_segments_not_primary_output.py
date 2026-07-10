import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "bad_transcript_run"


def test_selected_segments_not_primary_output():
    summary = json.loads((OUT / "workflow_summary.json").read_text(encoding="utf-8"))
    primary = "\n".join(summary["primary_outputs"])
    assert "selected_segment" not in primary
    assert "assets/selected_segments" not in primary
    assert "assets/selected_segments/" in summary["intermediate_assets"]
