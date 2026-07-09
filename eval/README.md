# ClipPilot-Agent Evaluation

This directory contains a small, application-oriented evaluation harness. It is designed to answer workflow questions, not public video summarization benchmark questions.

Compared systems:

- `rule_baseline`: subtitle parsing plus simple rule selection.
- `single_agent_baseline`: one LLM call for content selection and timeline planning.
- `multi_agent_harness`: the current Multi-Agent Editing Workflow Harness.

Human review fields are intentionally blank until a person fills the blinded review sheet. Judge scores are not used as human ratings.

Run:

```powershell
py -3.12 eval/run_eval.py --limit 5
py -3.12 eval/build_human_review_sheet.py
py -3.12 eval/aggregate_results.py
```
