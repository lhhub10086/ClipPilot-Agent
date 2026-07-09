from clip_pilot.agent import transcript_resolver


def test_transcript_resolver_requires_evidence(monkeypatch, tmp_path):
    def fake_call(messages, config):
        return {"success": True, "model": "fake", "json": {"sentence_id": "s1", "selected_text": "加速度是核心物理量。", "resolution_status": "resolved", "confidence": 0.7, "evidence_sources": [], "reason": "guess", "changed": True}}

    monkeypatch.setattr(transcript_resolver, "call_chat_completion", fake_call)
    result = transcript_resolver.resolve_one(
        original={"sentence_id": "s1", "refined_text": "信奥义"},
        recovery={"recovered_candidates": []},
        previous_text="",
        next_text="",
        block={},
        config={"llm": {"model": "fake"}},
        glossary=["加速度"],
        output_dir=str(tmp_path),
    )
    assert result["resolution_status"] == "unresolved"
    assert result["changed"] is False
