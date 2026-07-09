from __future__ import annotations

from clip_pilot.tools.coherence_validator import validate_semantic_timeline


def test_export_should_be_blocked_when_semantic_invalid():
    timeline = {"items": [{"source_start": 0, "text": "and this depends on prior context", "starts_mid_sentence": False, "ends_mid_sentence": False, "completeness_score": 0.2, "standalone_score": 0.2}]}
    result = validate_semantic_timeline(timeline)["data"]
    assert result["semantic_timeline_valid"] is False
