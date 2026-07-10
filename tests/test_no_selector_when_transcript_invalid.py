from pathlib import Path


def test_no_selector_editor_judge_artifacts_when_transcript_invalid():
    out = Path("tests/fixtures/bad_transcript_run")
    assert not (out / "selector_response.json").exists()
    assert not (out / "editor_timeline.json").exists()
    assert not (out / "judge_response_round_1.json").exists()
