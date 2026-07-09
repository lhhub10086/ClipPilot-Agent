import json
from pathlib import Path

from clip_pilot.tools.editing_unit_tool import build_editing_units


def test_editing_units_semantic_complete(tmp_path: Path):
    sentence_path = tmp_path / "sentence_units.json"
    block_path = tmp_path / "semantic_blocks.json"
    sentence_path.write_text(
        json.dumps(
            {
                "sentence_units": [
                    {"sentence_id": "s1", "start": 0, "end": 5, "refined_text": "今天讲加速度。", "sentence_complete": True},
                    {"sentence_id": "s2", "start": 5, "end": 10, "refined_text": "它描述速度变化快慢。", "sentence_complete": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    block_path.write_text(json.dumps({"semantic_blocks": [{"block_id": "b1", "topic": "加速度", "sentence_ids": ["s1", "s2"]}]}), encoding="utf-8")
    result = build_editing_units(sentence_units_path=str(sentence_path), semantic_blocks_path=str(block_path), output_path=str(tmp_path / "editing_units.json"))
    assert result["data"]["editing_units"][0]["semantic_complete"] is True
