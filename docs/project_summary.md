# Project Summary

## Background

Long-form course, interview, and tutorial videos often need first-cut review versions before a human editor can polish them. A naive LLM pipeline can select fragmented clips, ignore transcript risk, exceed duration policy, or export playable media that still fails the user task.

## Goal

ClipPilot-Agent is a Multi-Agent Editing Workflow Harness. It coordinates transcript processing, content selection, timeline editing, coherence judging, repair loops, export gates, media validation, trace logging, replay, and human review artifacts.

## Architecture

The system has four layers:

1. Transcript Layer
2. Multi-Agent Editing Layer
3. Harness Layer
4. Export Layer

The Harness controls execution and validation. Agents make content decisions.

## Multi-Agent Roles

- Content Selector chooses content candidates.
- Timeline Editor creates or repairs a rough-cut sequence.
- Coherence Judge reviews the assembled transcript.
- Repair Loop feeds structured problems back into timeline editing.

## Gates

The project includes Transcript Quality, Selection-Aware Transcript, Coherence, Task Coverage, Policy, Media, and Human Review gates. These gates stop bad transcripts, incoherent timelines, degenerate repairs, overlong videos, and invalid media from being labeled successful.

## Success Case

The good VTT case demonstrates that with an external subtitle, the workflow can run through selection, judging, repair, policy validation, FFmpeg export, media validation, and review artifact generation.

## Failure Case

The physics ASR case demonstrates the opposite: media export succeeded, but the timeline collapsed to one 20-second segment. Task Coverage Gate correctly marked `automated_validation_passed=false` and `production_ready=false`.

## Tests

The current suite reports `107 passed`. Tests cover Harness modules, schema contracts, transcript gates, repair loops, policy validation, media validation, task coverage, and UTF-8 review output.

## Current Limits

The system is not a benchmark-leading summarization model. It is a workflow harness that makes failures visible and prevents weak outputs from being mislabeled as successful.
