from __future__ import annotations

from clip_pilot.tools.coherence_validator import validate_semantic_timeline


def test_unresolved_reference_is_rejected():
    timeline = {"items": [{"source_start": 0, "text": "So it matters.", "starts_mid_sentence": False, "ends_mid_sentence": False, "completeness_score": 0.9, "standalone_score": 0.9}]}
    result = validate_semantic_timeline(timeline)["data"]["checks"]
    assert result["no_unresolved_reference"] is False
    assert result["semantic_timeline_valid"] is False
