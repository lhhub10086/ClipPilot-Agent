# Clean Environment Reproduction

## Environment

- Python: 3.12
- Platform: Windows local shell
- Clean environment: `.venv-clean`

## Commands

```powershell
py -3.12 -m venv .venv-clean
.\.venv-clean\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv-clean\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-clean\Scripts\python.exe -m compileall src scripts eval
.\.venv-clean\Scripts\python.exe -m pytest tests/ -q
```

CLI smoke checks:

```powershell
.\.venv-clean\Scripts\python.exe scripts/run_workflow.py --help
.\.venv-clean\Scripts\python.exe scripts/replay_run.py --help
.\.venv-clean\Scripts\python.exe scripts/run_subtitle_preview.py --help
.\.venv-clean\Scripts\python.exe scripts/apply_subtitle_review.py --help
.\.venv-clean\Scripts\python.exe scripts/validate_run.py --help
.\.venv-clean\Scripts\python.exe eval/run_eval.py --help
.\.venv-clean\Scripts\python.exe eval/build_human_review_sheet.py --help
.\.venv-clean\Scripts\python.exe eval/aggregate_results.py --help
```

## Result

- `compileall`: passed
- `pytest`: `124 passed`
- CLI help: passed for workflow, replay, subtitle preview, subtitle review, validation, and evaluation scripts.

## Issue Found and Fixed

Clean install initially failed one test because `cv2` was used by black-frame tests but OpenCV was not declared. The fix was to add `opencv-python-headless>=4.9` to `requirements.txt`.

## Notes

- No local `FireRed-OpenStoryline/` dependency was required.
- No real LLM key was required for tests.
- FFmpeg is still a system dependency for real video export; it is not installed through pip.
- `.venv-clean` was removed after verification and is ignored by `.gitignore`.
