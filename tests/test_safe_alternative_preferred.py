import json

from clip_pilot.tools.editing_unit_tool import annotate_semantic_blocks_with_risk


def test_safe_alternative_ids_attached_to_risky_block(tmp_path):
    blocks = tmp_path / "blocks.json"
    risks = tmp_path / "risks.json"
    out = tmp_path / "annotated.json"
    blocks.write_text(
        json.dumps(
            {
                "semantic_blocks": [
                    {"block_id": "risky", "topic": "加速度", "sentence_ids": ["s1"], "text": "加速度桥梁", "duration": 8},
                    {"block_id": "safe", "topic": "加速度", "sentence_ids": ["s2"], "text": "加速度定义", "duration": 8},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    risks.write_text(json.dumps({"risks": [{"sentence_id": "s1", "risk_score": 0.7}]}), encoding="utf-8")
    annotate_semantic_blocks_with_risk(semantic_blocks_path=str(blocks), asr_risk_report_path=str(risks), output_path=str(out))
    payload = json.loads(out.read_text(encoding="utf-8"))["semantic_blocks"]
    risky = next(block for block in payload if block["block_id"] == "risky")
    assert risky["safe_alternative_ids"] == ["safe"]
