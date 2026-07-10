# Local Artifact Cleanup Report

Date: 2026-07-10

## Removed Local Directories

- `outputs/`
  - Reason: generated workflow/demo/evaluation outputs are not source artifacts.
  - Git status: ignored and not tracked.
  - Replacement: tests now use `tests/fixtures/bad_transcript_run/` instead of root `outputs/workflow_run`.

- `data/`
  - Reason: local reference videos, downloaded datasets, extracted frames, transcripts, and demo videos are not required by the committed project or automated tests.
  - Included local reference material such as EDUVSUM, TVSum, VidChapters-related files, demo videos, extracted frames, and generated metadata.
  - Approximate removed size before cleanup: 7.7 GB.
  - Git status: ignored and not tracked.

## Preserved

- Source code: `src/`
- Scripts: `scripts/`
- Evaluation framework: `eval/`
- Tests and fixtures: `tests/`
- Documentation and examples: `docs/`, `examples/`
- Git tag and commits.

## Reproducibility Notes

The GitHub repository is intentionally lightweight. To run real video demos again, prepare local data outside Git and pass paths through CLI arguments or environment variables. The committed tests do not require local videos, downloaded datasets, `outputs/`, or `data/`.

## Verification

After cleanup:

- `outputs/`: removed
- `data/`: removed
- `eval/outputs/`: contains only `.gitkeep`
- `pytest`: `124 passed`
- `compileall`: passed
