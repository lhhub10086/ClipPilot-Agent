# Untracked Directories Audit

## FireRed-OpenStoryline/

- Purpose: local third-party reference repository.
- Submit to ClipPilot-Agent: no.
- Action: ignored by `.gitignore`.
- Mainline dependency: none found in imports, scripts, tests, README, or configs.
- Note: ClipPilot-Agent references FireRed-style architecture ideas but does not vendor the third-party code.

## app/

- Purpose: legacy Streamlit dashboard.
- Submit to current release: no.
- Action: ignored by `.gitignore`.
- Mainline dependency: none found.
- Rationale: current release focuses on Workflow Harness, CLI, docs, examples, and evaluation framework.

## archive/

- Purpose: local historical source/eval/config/script archive.
- Submit to current release: no.
- Action: ignored by `.gitignore`.
- Mainline dependency: none found.
- Rationale: useful locally for provenance, but not needed for installation or CI.

## archive_before_cleanup/

- Purpose: pre-cleanup snapshot.
- Submit to current release: no.
- Action: ignored by `.gitignore`.
- Mainline dependency: none found.
- Rationale: local backup only.
