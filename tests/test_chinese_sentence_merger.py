from clip_pilot.tools.sentence_segment_tool import build_sentences


def test_chinese_sentence_merger_uses_chinese_punctuation():
    cues = [
        {"start": 0.0, "end": 2.0, "text": "今天我们讲加速度，"},
        {"start": 2.1, "end": 4.0, "text": "它描述速度变化快慢。"},
        {"start": 4.2, "end": 6.0, "text": "然后看一个例题，"},
        {"start": 6.1, "end": 8.0, "text": "比较两辆车。"},
    ]

    result = build_sentences(cues)
    texts = [item["text"] for item in result["data"]["sentences"]]

    assert len(texts) == 2
    assert texts[0].endswith("。")
    assert "然后看一个例题" in texts[1]
