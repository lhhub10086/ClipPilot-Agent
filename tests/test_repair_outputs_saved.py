import json

from clip_pilot.agent.timeline_repair import run_timeline_repair_round


def test_repair_outputs_saved(tmp_path):
    timeline = {"timeline_items": [{"segment_id": "segment_001", "source_start": 0, "source_end": 8, "duration": 8, "transcript": "A complete sentence.", "source_block_ids": ["block_1"]}]}
    judge = {"repair_instruction": {"insert_bridges": [{"segment_id": "segment_001", "bridge_after": "Bridge."}]}, "major_problems": []}
    result = run_timeline_repair_round(editor_timeline=timeline, judge_response=judge, output_dir=str(tmp_path), round_index=1)
    repair_dir = tmp_path / "repair_round_1"
    assert result["success"] is True
    assert (repair_dir / "editor_timeline.json").exists()
    assert (repair_dir / "final_review_transcript.md").exists()
    assert (repair_dir / "repair_actions_applied.json").exists()
    actions = json.loads((repair_dir / "repair_actions_applied.json").read_text(encoding="utf-8"))
    assert actions["timeline_changed"] is True
