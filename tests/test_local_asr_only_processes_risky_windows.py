import json
from pathlib import Path

from clip_pilot.tools import local_asr_recovery_tool


def test_local_asr_only_processes_risky_windows(monkeypatch, tmp_path: Path):
    risk_report = {
        "risks": [
            {"sentence_id": "s1", "start": 10, "end": 12, "text": "信奥义", "risk_score": 0.9},
            {"sentence_id": "s2", "start": 20, "end": 22, "text": "低风险", "risk_score": 0.4},
        ]
    }
    risk_path = tmp_path / "risk.json"
    risk_path.write_text(json.dumps(risk_report), encoding="utf-8")
    calls = []

    def fake_recover(**kwargs):
        calls.append(kwargs["risk"]["sentence_id"])
        return {"sentence_id": kwargs["risk"]["sentence_id"], "recovered_candidates": []}

    monkeypatch.setattr(local_asr_recovery_tool, "recover_one_window", fake_recover)
    result = local_asr_recovery_tool.recover_risky_windows(video_path="video.mp4", risk_report_path=str(risk_path), output_dir=str(tmp_path), config={}, threshold=0.65)
    assert calls == ["s1"]
    assert result["data"]["processed_count"] == 1
