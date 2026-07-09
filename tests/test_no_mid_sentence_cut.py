from __future__ import annotations

from clip_pilot.tools.coherence_validator import validate_semantic_timeline


def test_mid_sentence_cut_invalidates_timeline():
    timeline = {"items": [{"source_start": 0, "text": "A complete thought.", "starts_mid_sentence": True, "ends_mid_sentence": False, "completeness_score": 0.9, "standalone_score": 0.9}]}
    checks = validate_semantic_timeline(timeline)["data"]["checks"]
    assert checks["no_mid_sentence_cut"] is False
    assert checks["semantic_timeline_valid"] is False
