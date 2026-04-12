---
name: run-experiment
description: Invoke AI Creature Field Study experiment scripts (experience_effect, duo) with the correct brain identifiers, seeds, and output paths. Use this whenever running, re-running, or reproducing any wilderness experiment in this repo.
---

# Run Experiment

This skill documents how to execute the experiments in `experiments/`. Use it for every experimental run.

## Scripts

| Script | What it does |
|---|---|
| `experiments/experience_effect_experiment.py` | Group A (wilderness #1 → reflect → wilderness #2) vs Group B (fresh → wilderness #2). Tests whether lived experience changes behavior. |
| `experiments/duo_experiment.py` | Two creatures share a wilderness. Tests social context effect. |

## Invocation

Always activate the venv first:

```bash
source .venv/bin/activate
```

### Experience effect

```bash
python experiments/experience_effect_experiment.py \
  --brain claude_cli:haiku \
  --seeds 42,99,7
```

- `--brain` takes `provider:model`, e.g. `claude_cli:haiku`, `gemini_cli:gemini-2.5-flash`.
- `--seeds` is comma-separated ints. Default is the script's own default (inspect the file before assuming).

### Duo

```bash
python experiments/duo_experiment.py \
  --brains claude_cli:haiku,gemini_cli:gemini-2.5-flash
```

- `--brains` is comma-separated `provider:model` pairs (2 creatures).

## Output locations

| Experiment | Output dir |
|---|---|
| Experience effect | `experiments/experience_results/<provider>_<model>/` |
| Duo | `experiments/duo_results/` |
| Duo repro | `experiments/duo_repro/run{1,2,3}/` |

Per-run files to expect:
- `train_*` / `test_*` subdirs — habitat snapshots
- `report_*.md` — auto-generated session reports
- `summary.json` — aggregate metrics
- `wilderness_*.json` — raw tick data (inside run subdirs)

## Pre-flight checks

Before invoking:
1. Venv active? (`which python` → should be inside `.venv`)
2. Required CLI installed? Claude CLI for `claude_cli:*`, Gemini CLI for `gemini_cli:*`.
3. Prior results — will this overwrite? If yes, confirm with user.

## Why seeds matter

The seed controls wilderness event order. Reproducibility claims in the paper depend on identical seeds producing identical event sequences. Never mix or fabricate seeds. If a run doesn't specify one, state which default was used.

## Post-run verification

After a run completes:
- Check exit code is 0.
- Confirm expected output files exist.
- Sample one `wilderness_*.json` — did it reach the expected tick count?

Report any discrepancy; do not silently retry.
