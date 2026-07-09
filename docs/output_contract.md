# Output Contract

ClipPilot-Agent outputs are grouped by product role.

## Primary Outputs

- `final_review.mp4`: first-cut review video, only generated when export is allowed.
- `timeline.json`: source-to-target editing timeline.
- `final_review_transcript.md`: readable transcript assembled from the proposed timeline.
- `validation_report.json`: gate-level validation result.
- `workflow_summary.json`: compact run summary for dashboards and reports.

## Supporting Outputs

- `final_review.srt`
- `trace.json`
- `selector_response.json`
- `editor_timeline.json`
- `judge_response*.json`
- `policy_validation_report.json`
- `task_coverage_report.json`
- `export_gate_decision.json`
- `human_final_review_checklist.md`
- `human_review_sheet.csv`

## Intermediate Assets

- `assets/selected_segments/`
- `assets/normalized_segments/`
- `assets/temp_chunks/`
- subtitle preview files
- `repair_round_*/`

Intermediate assets are not user deliverables. They exist to support debugging, replay, and media assembly.

## Validation Semantics

`run_completed=true` means the workflow did not crash. It does not mean the product succeeded.

`automated_validation_passed=true` requires:

```text
transcript_valid
&& selected_scope_lexical_valid
&& content_coherence_valid
&& task_coverage_valid
&& content_sufficiency_valid
&& policy_valid
&& media_valid
```

`production_ready=true` requires human review acceptance.
