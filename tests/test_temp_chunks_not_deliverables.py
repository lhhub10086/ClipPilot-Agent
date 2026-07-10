import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "bad_transcript_run"


def test_temp_chunks_not_deliverables():
    summary = json.loads((OUT / "workflow_summary.json").read_text(encoding="utf-8"))
    assert "temp_chunks" not in "\n".join(summary["primary_outputs"])
    assert "assets/temp_chunks/" in summary["intermediate_assets"]
