from clip_pilot.tools.editing_unit_tool import _make_unit


def test_sentence_units_are_grouped_into_editing_unit():
    units = [
        {"sentence_id": "s1", "start": 0, "end": 3, "refined_text": "第一句。", "sentence_complete": True},
        {"sentence_id": "s2", "start": 3, "end": 9, "refined_text": "第二句解释完整意思。", "sentence_complete": True},
    ]
    editing = _make_unit(1, units, {"topic": "加速度"})
    assert editing["sentence_ids"] == ["s1", "s2"]
    assert editing["duration"] == 9
    assert editing["editing_unit_id"] == "editing_unit_0001"
