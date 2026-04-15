# Walkable Genotypes — AI Creature Field Study

> **Cross-environment validation of the Four Shell Model in AI Creatures.**
> Companion repository to a paper in the Model Medicine series.

[**Project page →**](https://jihoonjeong.github.io/ai-creature-field-study/) · [**Paper (PDF)**](docs/assets/walkable_genotypes.pdf) · [**Working draft (Markdown)**](docs/paper-draft.md) · [**Model Medicine**](https://jihoonjeong.github.io/model-medicine/)

---

## What this is

A small, replication-disciplined field study of how two LLM-backed AI creatures behave in a shared, seed-deterministic environment ("Wilderness"). The headline result is one surviving behavioral finding — **brain-fixed behavioral attractors with within-pair amplification** — that independently reproduces a Core-property prediction from Jeong (2026, arXiv:2603.04722) in a different environment.

Just as important is what *did not* survive. Five behavioral observations made it into early write-ups; four collapsed into their own sample stdev when re-run at n=5 with the same seeds; one survived three progressively stricter falsifiers at n=10. The methodology that distinguishes the survivor from the noise is the paper's primary contribution.

## Quick links

- **Pre-arXiv draft (PDF):** [`docs/assets/walkable_genotypes.pdf`](docs/assets/walkable_genotypes.pdf)
- **Working draft (Markdown):** [`docs/paper-draft.md`](docs/paper-draft.md)
- **Project page:** https://jihoonjeong.github.io/ai-creature-field-study/
- **Figures:** [`figures/walkable_genotypes/`](figures/walkable_genotypes/) — both Tier-A figures with regenerable scripts and a committed data snapshot
- **Experiment scripts:** [`experiments/`](experiments/)

## Reproducing the experiments

```bash
git clone https://github.com/JihoonJeong/ai-creature-field-study.git
cd ai-creature-field-study
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

LLM access is via local CLI subprocesses (Claude CLI for Haiku, Gemini CLI for Flash). A Claude Max / Gemini Ultra subscription is sufficient — no paid HTTP API calls are made.

```bash
# n=10 confirmation, Pair A (Haiku + Flash)
python experiments/duo_experiment.py \
  --brains claude_cli:haiku,gemini_cli:gemini-2.5-flash \
  --ticks 10 \
  --train-seeds 42,99,7,13,55,1,23,77,100,200 \
  --test-seed 123 \
  --output-dir experiments/smoke/my_rerun

# Same for Pair B (Haiku + Haiku) and Pair C (Flash + Flash) by changing --brains.
```

Re-runs will not produce bit-exact matches against the paper's numbers — LLM responses are not seedable — but should fall within the reported stdev bands. The Wilderness *event stream* is bit-exact deterministic per seed; see §3 of the paper draft.

## Reproducing the figures

```bash
pip install -r requirements-figures.txt
python figures/walkable_genotypes/figure1_attractor_separation.py
python figures/walkable_genotypes/figure2_walkback_audit.py
```

Both scripts load committed JSON snapshots from `figures/walkable_genotypes/data/` so the figures are bit-reproducible without re-running experiments.

## Repository layout

```
.
├── docs/                     Project page (GitHub Pages) + paper-draft.md
├── experiments/              Two experiment scripts + result snapshots
├── figures/walkable_genotypes/   Figure scripts + data snapshot
├── ludex/                    Subset of the Ludex organ library used by the experiments
├── requirements.txt          Experiment runtime deps
└── requirements-figures.txt  Figure & statistics deps (matplotlib, scipy)
```

## Citation

If you use this work, please cite both this companion repository and Jeong (2026):

```bibtex
@misc{walkable_genotypes_2026,
  author = {Jeong, Jihoon},
  title  = {Walkable Genotypes: Cross-Environment Validation of the Four Shell Model in AI Creatures},
  year   = {2026},
  url    = {https://jihoonjeong.github.io/ai-creature-field-study/}
}

@article{jeong2026model_medicine,
  author = {Jeong, Jihoon},
  title  = {Model Medicine: A Clinical Framework for Understanding, Diagnosing, and Treating AI Models},
  year   = {2026},
  eprint = {2603.04722},
  archivePrefix = {arXiv}
}
```

## License

[MIT](LICENSE).
