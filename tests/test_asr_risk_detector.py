from clip_pilot.tools.asr_risk_detector import build_risk_report


def test_asr_risk_detector_flags_semantic_anomalies():
    units = [{"sentence_id": "sentence_0001", "start": 1.0, "end": 3.0, "refined_text": "你们数量之后，大家都是信奥义的。"}]
    report = build_risk_report(units, [], glossary=["高中物理"], threshold=0.5)
    assert report["risk_sentence_count"] == 1
    assert "semantic_anomaly" in report["risks"][0]["risk_types"]
    assert report["risks"][0]["requires_re_asr"] is True
