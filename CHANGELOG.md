# Changelog

## v1.0.0-harness

### Added

- Multi-Agent Selector / Editor / Judge roles.
- Judge-driven Repair Loop.
- Transcript / Selection Scope / Coherence / Coverage / Policy / Media Gates.
- ToolRegistry / RunContext / StepExecutor / TraceRecorder.
- Replay and ArtifactValidator.
- FFmpeg first-cut export path.
- Success and failure examples.
- Rule / single-agent / multi-agent evaluation harness.

### Fixed

- Black-screen output false success.
- Duration policy overflow.
- Fixed three-segment default behavior.
- Degenerate single-segment false success.
- Validation success status semantics.
- UTF-8 human checklist output.

### Known Limitations

- Strong dependency on subtitle quality.
- Chinese ASR errors remain difficult.
- Human review is required.
- Human evaluation is pending.
- Outputs are first-cut artifacts, not publish-ready videos.
- No benchmark superiority claim.
