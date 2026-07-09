# Interview Guide

## 30-Second Intro

ClipPilot-Agent is a Multi-Agent Editing Workflow Harness for long videos. It does not claim to automatically create publish-ready edits. It coordinates transcript processing, content selection, timeline editing, LLM judging, repair loops, FFmpeg export, trace logging, validation gates, and human review artifacts.

## 2-Minute Intro

The project started from a common LLM video-editing failure: the system can export an MP4, but the result may be incoherent, overlong, based on bad subtitles, or reduced to one easy segment that no longer satisfies the user intent. I restructured the project as a workflow harness. Content Selector chooses candidate content, Timeline Editor builds a timeline, Coherence Judge reviews the assembled transcript, and repair loops feed structured feedback back to the editor. The Harness records every step, enforces gates, validates artifacts, supports replay, and keeps human review explicit.

## Why Not One LLM?

One LLM doing everything tends to generate and approve its own output. Splitting roles gives each agent an independent schema and responsibility:

- Selector chooses content.
- Editor creates a timeline.
- Judge evaluates transcript coherence.
- Validators check task coverage, policy, and media.

This makes failures easier to locate and enables repair loops instead of silent acceptance.

## Harness

Harness means execution control rather than content strategy. It manages ToolRegistry, RunContext, StepExecutor, TraceRecorder, ArtifactValidator, Mock Backend, and Replay.

## Repair Loop

When the Judge fails a timeline, it returns major problems, segment feedback, and repair instructions. The Timeline Editor repairs the timeline, the final transcript is regenerated, and the Judge runs again. Policy and coverage failures can also trigger repair.

## Transcript Quality Gate

The gate checks coverage, timestamps, garbled text, fragmentation, and structure. If the transcript is not usable, the system blocks editing instead of asking downstream agents to repair bad source text.

## Selection-Aware Gate

Global ASR errors do not always block editing. The system checks whether the selected content depends on unresolved ASR errors. Only selected-scope risk blocks or triggers targeted manual review.

## Task Coverage Gate

This gate was added after a real failure: a repair loop produced a coherent single 20-second segment, but it did not satisfy the course-review task. The gate checks required goals and narrative roles so media validity and coherence do not masquerade as product success.

## Media Valid Is Not Product Success

An MP4 can be playable, non-black, and have audio while still failing the editing task. ClipPilot-Agent separates `media_valid` from `automated_validation_passed`.

## Failure Case

The Chinese physics video exported valid media, but the final timeline collapsed to one short segment. The system now marks it as `degenerate_single_segment_output`, `automated_validation_passed=false`, and `production_ready=false`.

## What I Would Improve Next

- Better Chinese ASR and multiple ASR backends.
- OCR evidence for hard subtitles.
- More robust coverage scoring.
- Better editor policies for expanding context without overlong videos.
- More human-reviewed cases.

## Code Details To Discuss

- Trace event schema and replay.
- How sentence units and semantic blocks differ.
- How policy validation blocks overlong timelines.
- How task coverage prevents degenerate repair.
- How FFmpeg export is validated with media probes.
