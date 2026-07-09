# Human Review Guide

This guide explains how to fill `eval/outputs/human_review_sheet.csv`.

## How to Review

1. Open each anonymous `output_id` artifact listed in the sheet.
2. Read the user intent and inspect the produced rough-cut artifacts.
3. Do not look up which system produced the output.
4. Do not use Judge scores, Gate states, or `automated_validation_passed` as human ratings.
5. Fill the score columns from 1 to 5.
6. Choose one `human_decision`: `acceptable`, `needs_minor_edit`, or `unacceptable`.
7. Save the CSV.
8. Run:

```powershell
py -3.12 eval/aggregate_results.py --results eval/outputs/results.csv
```

## Score Meaning

- `1`: essentially fails the criterion.
- `2`: weak and hard to use.
- `3`: partially usable but clearly flawed.
- `4`: mostly works with minor issues.
- `5`: strong for a first-cut review artifact.

## Decision Meaning

- `acceptable`: good enough as a first-cut artifact.
- `needs_minor_edit`: useful but needs human trimming or correction.
- `unacceptable`: not worth continuing from this output.

## Failure Cues

Use low scores when you see black frames, broken audio, mid-sentence cuts, topic jumps, missing task coverage, overlong outputs, degenerate single-segment outputs, or severe subtitle errors.

## Reviewers

Current protocol supports a single reviewer. If multiple reviewers are used later, save separate files such as `reviewer_1.csv` and `reviewer_2.csv`, then aggregate them separately before comparing agreement.
