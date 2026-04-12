---
name: analyze-results
description: Parse and interpret experiment result files (wilderness_*.json, summary.json, report_*.md) to compute behavioral metrics and compare conditions. Use whenever analyzing any run output, comparing brains or conditions, or producing metric tables for the paper.
---

# Analyze Results

This skill defines the result schema and standard metrics for the Field Study. Use it every time you interpret experiment output.

## Result file layout

```
experiments/<experiment>_results/
├── <provider>_<model>/            # one subdir per brain config
│   ├── train_<cond>_r<N>/         # habitat snapshot for each run
│   │   └── wilderness_*.json      # raw tick data
│   ├── test_<cond>_r<N>/
│   ├── report_<cond>_r<N>.md      # auto-generated per-run narrative
│   └── summary.json               # aggregate metrics across runs
```

`<cond>` is usually `a` (experienced) or `b` (fresh) for the experience_effect experiment, or role labels for duo.

## Raw tick JSON structure

Each `wilderness_*.json` contains an ordered list of ticks. Each tick typically has:
- `tick` — integer index
- `event` — environmental stimulus
- `action` — creature's chosen action (explore, defend, support, trade, rest, etc.)
- `emotion` — current emotional state
- `energy` — remaining energy
- `reasoning` — brain's rationale (text)

When the schema differs (new fields, renames), read the actual file — don't assume.

## Standard metrics

From `experiment_design.md`:

| Metric | Formula |
|---|---|
| Action diversity | `distinct_actions / total_actions` |
| Emotion diversity | `distinct_emotions_across_ticks` |
| Cooperation rate | `(support + trade) / total_actions` |
| Defend rate | `defend / total_actions` |
| Explore rate | `explore / total_actions` |
| Final energy | `ticks[-1].energy` |
| Emotion trajectory | ordered list of `tick.emotion` |

Prefer values already in `summary.json` when present; recompute from raw ticks only to verify or when summary is missing.

## Comparison patterns

- **Experience effect:** compare Group A (experienced) vs Group B (fresh) on same seed. The *difference* is the effect of lived memory, because events are identical.
- **Duo effect:** compare solo-baseline metrics (from experience_results) vs duo metrics for same brain. Defend rate and emotion valence are the headline metrics here.
- **Brain comparison:** always hold seed + condition constant.

## Reporting format

When producing an analysis, output in this order:

1. **Setup line:** experiment, brains, seeds, n runs.
2. **Metrics table:** one row per condition, columns for each metric.
3. **Interpretation:** 2-4 sentences. What the numbers show. Point at surprises.
4. **Caveats:** n, missing runs, any anomalies.

Never report a comparison without stating n. A single seed is an anecdote; say so.

## Honesty rules

- If Group A and Group B differ by less than run-to-run variance within a group, the "effect" is noise — say that.
- If a metric contradicts prior stated findings (see CODY_HANDOFF.md), flag it; don't discard.
- If `summary.json` and raw ticks disagree, report both values.
