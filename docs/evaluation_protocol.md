# Evaluation Protocol

This evaluation measures whether ClipPilot-Agent behaves like a reliable rough-cut workflow harness. It does not measure SOTA video summarization performance.

## Systems

1. `rule_baseline`: rule-based subtitle selection and basic media validation.
2. `single_agent_baseline`: one LLM plans selection and content in a single step.
3. `multi_agent_harness`: transcript gates, Selector, Timeline Editor, Coherence Judge, Repair Loop, Coverage Gate, Policy Gate, Export Gate, and Media Gate.

All systems must use the same video, subtitle, intent, duration constraints, and media export parameters for a case.

## Human Review

The human review sheet is blinded: it uses anonymous `output_id` values and does not show `system_name`. Human fields remain empty until reviewed by a person.

Scores use 1-5 scales for task completion, coherence, sentence integrity, content value, subtitle accuracy, rough-cut usability, and overall quality. The final decision is one of:

- `acceptable`
- `needs_minor_edit`
- `unacceptable`

LLM Judge scores must not be copied into human fields.

## Core Metrics

- Useful Completion Rate
- Acceptable-or-Minor Rate
- Bad Output False Acceptance Rate
- Bad Output Rejection Recall
- Repair Success Rate
- Degenerate Output Rate
- Export Allow Rate
- Manual Review Rate
- Gate Block distribution
- Engineering cost: LLM calls, tokens, estimated cost, latency, repair rounds

These metrics must be interpreted together. A system that blocks every output may have low false acceptance but also zero useful completion.
