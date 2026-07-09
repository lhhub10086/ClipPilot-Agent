# Harness Design

The Harness is the run-control layer for ClipPilot-Agent. It does not decide what content is important and does not claim that a video is good. It makes every tool call, agent call, repair decision, gate result, and artifact auditable.

## Modules

- `ToolRegistry`: registers callable tools by name.
- `RunContext`: stores input paths, output paths, config, task state, and generated artifact references.
- `StepExecutor`: executes one named step, captures output, duration, success, and error.
- `TraceRecorder`: writes `trace.json` with tool and LLM events.
- `ArtifactValidator`: checks the final output contract and gate results.
- `MockBackend`: supports explicit test doubles; mock use must be visible in trace/summary.
- `Replay`: reads trace artifacts for debugging and reproducibility.

## Responsibility Boundary

Planner and agents decide content strategy:

- what task type the intent implies;
- what topics are worth selecting;
- how timeline items should be ordered;
- whether repair should expand, replace, reduce scope, or request manual review.

Harness controls execution:

- save Planner output;
- drive the workflow according to the plan;
- call tools and agents;
- record trace;
- write reports;
- enforce gates;
- block invalid exports;
- support replay.

## Quality Gates

### 1. Transcript Quality Gate

Checks subtitle coverage, empty text ratio, garbled text, fragmented timing, timestamp monotonicity, and sentence structure. Bad transcripts are blocked before editing agents run.

### 2. Selection-Aware Transcript Gate

Global transcript risk does not automatically block editing. The gate checks whether the selected content depends on unresolved ASR errors. If unresolved text is outside the selected scope, editing may continue with exclusions.

### 3. Coherence Judge Gate

Reviews the assembled final transcript for mid-sentence cuts, missing context, unresolved references, topic jumps, weak transitions, and fragmented sequence design.

### 4. Repair Loop

Judge or policy failures are returned to the Timeline Editor. The loop can replace segments, expand context, reduce scope, or request targeted manual review. It must not silently pass weak timelines.

### 5. Task Coverage Gate

Prevents a repair from improving coherence by deleting task-critical content. A single coherent 20-second segment can still fail if it does not cover the user's requested review goals.

### 6. Policy Enforcement Gate

Checks segment count, segment duration, final duration, and Planner policy. A coherent timeline that exceeds the policy is not exportable.

### 7. Media Validation Gate

Checks whether `final_review.mp4` is decodable, has audio when expected, is not mostly black, is not frozen for long spans, and matches the timeline duration and subtitle duration.

### 8. Human Review Gate

The system generates a checklist but never marks the work as accepted. `production_ready=true` requires `automated_validation_passed=true` and `human_review_status=acceptable`.

## Why This Matters

The physics failure case showed that media can be valid while the product is invalid. Harness gates make that distinction explicit.
