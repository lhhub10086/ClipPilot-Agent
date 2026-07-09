import pytest

from eval.schemas.eval_case_schema import EvalCase


def test_eval_case_requires_core_fields():
    with pytest.raises(ValueError):
        EvalCase.from_dict({"case_id": "x"})


def test_eval_case_accepts_env_paths():
    case = EvalCase.from_dict(
        {
            "case_id": "case_1",
            "category": "good_vtt",
            "video_path": "${CLIPPILOT_DATA_ROOT}/video.mp4",
            "subtitle_path": "${CLIPPILOT_DATA_ROOT}/video.vtt",
            "language": "en",
            "intent": "Make a review cut.",
            "expected_behavior": "export_or_valid_block",
        }
    )
    assert case.case_id == "case_1"
    assert "CLIPPILOT_DATA_ROOT" in case.video_path
