---
name: session-report
description: Generate or interpret per-run session reports using ludex/viewers/session_report.py. Use whenever narrating a single run's behavior, producing report_*.md files, or summarizing tick-by-tick creature experience for the paper.
---

# Session Report

Session reports are the human-readable narrative of a single run. They are auto-generated during experiment execution, but can be regenerated post-hoc from raw tick data.

## Generator

```python
from ludex.viewers.session_report import generate_report
```

The experiment scripts already call this. Regenerate manually only when:
- A report file is missing but the raw `wilderness_*.json` exists.
- The generator changed and you want to refresh old runs.

## Report structure

A typical `report_*.md` contains, per tick:
- event
- creature's action
- creature's emotion
- brief reasoning snippet

Plus a header with run metadata (brain, seed, condition) and a footer with aggregate metrics.

## When to use session reports vs raw ticks

- **Narrating a run for the paper or README:** use the session report. It's already curated.
- **Computing metrics or comparing conditions:** use raw ticks / `summary.json`. Reports are lossy.
- **Spotting behavioral anomalies:** skim the report first, then dig into the specific tick in the JSON.

## Regeneration

If you need to regenerate:

1. Locate the run's `wilderness_*.json` under the appropriate `train_*` or `test_*` subdir.
2. Call `generate_report(wilderness_json_path, output_md_path)`.
3. Verify the output file is written and non-empty.

Inspect `ludex/viewers/session_report.py` for the exact function signature before invoking — it may accept additional args (habitat path, metadata) depending on current state.

## Interpreting a report for paper prose

When translating a report into paper language:

- Don't quote the reasoning field verbatim without marking it as creature output.
- Describe the trajectory (e.g. "cautious early → exploratory after tick 4") rather than listing every tick.
- Cite the report file path so readers can verify: `experiments/experience_results/claude_cli_haiku/report_a_r1.md`.
- Never conflate one run's narrative with a general claim about the brain. Say "in this run" or cite n.
