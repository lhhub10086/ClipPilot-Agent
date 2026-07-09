# Success Case: Good VTT Course Video

## Input

- Video: EDUVSUM Crash Course computer science sample.
- Subtitle: provided English VTT.
- Intent: create a coherent first-cut review video for students.

## Result

The workflow ran through transcript validation, content selection, timeline editing, judge review, repair, policy validation, export gate, FFmpeg final video generation, media validation, and review artifact generation.

## Artifacts

Example artifacts are stored in:

```text
examples/success_case_good_vtt/
outputs/demo_success/
```

Key files:

- `task_plan.json`
- `selector_response.json`
- `editor_timeline.json`
- `final_review_transcript.md`
- `judge_response_round_1.json`
- `policy_validation_report.json`
- `export_gate_decision.json`
- `timeline.json`
- `validation_report.json`
- `workflow_summary.json`

`final_review.mp4` is a local output artifact, not a benchmark claim.

## Notes

Human review is still required before any production use. This case demonstrates workflow closure, not video summarization superiority.
