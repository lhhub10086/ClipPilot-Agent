# Failure Case: Chinese Physics ASR

## Input

- Video: Chinese physics bridge lesson.
- Subtitle source: ASR/refined transcript pipeline.
- Intent: create a quick review rough cut for students.

## What Happened

The exported media was technically valid:

- playable MP4;
- audio present;
- no black-screen failure;
- timeline explainable.

But the product result failed:

- final output contained only 1 segment;
- duration was 20 seconds;
- content covered only the opening discussion;
- Judge coherence score improved to `0.85`;
- task coverage score was only `0.562`;
- required goal "学习方法提醒" was not covered;
- narrative roles such as core explanation and closing were missing.

## Final Status

```json
{
  "automated_validation_passed": false,
  "production_ready": false,
  "human_review_status": "unacceptable",
  "failed_reason": "degenerate_single_segment_output"
}
```

## Why This Case Matters

This case proves that ClipPilot-Agent can distinguish media success from task success. A playable video is not enough. Task Coverage Gate blocks degenerate single-segment repairs from being mislabeled as successful.
