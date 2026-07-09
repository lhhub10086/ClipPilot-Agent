from clip_pilot.tools.editing_unit_tool import annotate_block


def test_medium_risk_bridge_is_review_if_selected_not_silent_exclusion():
    block = {"block_id": "b1", "sentence_ids": ["s1"], "text": "那么接下来解释高中物理学习方法。", "duration": 10, "block_type": "transition"}
    annotated = annotate_block(block, {"s1": {"risk_score": 0.6}})
    assert annotated["lexical_risk_level"] == "medium_risk"
    assert annotated["review_if_selected"] is True
    assert annotated["bridge_importance"] > 0
