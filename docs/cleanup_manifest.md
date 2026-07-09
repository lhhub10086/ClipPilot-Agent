# Cleanup Manifest

## Removed Or Curated

Historical run outputs were removed from `outputs/` after preserving final examples:

- repeated workflow runs;
- subtitle preview scratch outputs;
- temporary ASR cache outputs;
- old repair experiments;
- redundant logs and MP4 files.

## Kept

- `outputs/demo_success/`
- `outputs/demo_failure/`
- `outputs/latest_run/`
- `examples/success_case_good_vtt/`
- `examples/failure_case_physics_asr/`
- `data/raw/`
- `archive/legacy_eval/`
- `archive/legacy_eduvsum_eval/`
- `tests/`
- `docs/`
- `configs/`

## Archived

Historical benchmark and evaluation code was moved out of the mainline source tree:

```text
archive/legacy_eval/eval/
```

Legacy root-level configs were moved to:

```text
archive/legacy_configs/
```

Legacy root-level source packages were moved to:

```text
archive/legacy_src/
```

One-off API debugging scripts were moved to:

```text
archive/legacy_scripts/
```

## Regeneration

Run a fresh workflow with:

```powershell
py -3.12 scripts/run_workflow.py --video path/to/video.mp4 --subtitle path/to/subtitle.vtt --intent "Create a coherent first-cut review video." --out outputs/demo_run
```

Add `--export-video` only when video export is intended and gates allow it.
