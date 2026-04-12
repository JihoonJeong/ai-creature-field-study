# Cody Handoff — AI Creature Field Study (Public Repo)

## What this is

This is the **public companion repo** for a research paper:
**"Experience and Social Context Shape Behavior in AI Creatures"**

The parent project is **Ludex** (private) — a biological agent block library
that assembles AI creatures from modular organs (memory, emotion, immune, etc.).
This repo contains only the code and data needed to **reproduce the paper's experiments**.

## Relationship to Ludex

- **Ludex (private):** full organ library, GRAND_PLAN, all design decisions, living creatures (Primo, Spark, etc.)
- **This repo (public):** experiment code, field implementations, results data, paper-specific documentation

Changes made here should be reviewed and potentially backported to Ludex.
Changes from Ludex should be selectively forward-ported here.

## What's here

### Code
- `ludex/` — subset of the Ludex organ library needed for experiments
  - `core/` — Organism, Habitat, Selfhood (SELF.md), Consolidation (dream cycle), Prompt templates
  - `blocks/` — Engine, Provider, Memory, Emotion, Immune, Resilience, Tracking
  - `fields/` — Wilderness (event-driven environment), Agora (free conversation)
  - `skills/` — brain-agnostic learned behaviors
  - `viewers/` — Session report generator

### Experiments
- `experiments/experience_effect_experiment.py` — does lived experience change behavior?
- `experiments/duo_experiment.py` — how does social presence affect behavior?
- `experiments/experiment_design.md` — full experimental protocol

### Key findings so far
1. **Experience makes creatures cautious (Haiku) or less defensive (Flash)** — brain-dependent, opposite directions
2. **Social presence eliminates defensive behavior** — defend drops from 13-20% solo to 3% duo
3. **Emotion flips from negative to positive in duo** — afraid/hostile → hopeful/loving

## How to reproduce

```bash
# Prerequisites
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Claude Code CLI (for Haiku experiments)
# Already installed if you have Claude Max subscription

# Gemini CLI (for Flash experiments)  
npm install -g @google/gemini-cli

# Run experience effect experiment
python experiments/experience_effect_experiment.py --brain claude_cli:haiku --seeds 42,99,7

# Run duo experiment
python experiments/duo_experiment.py --brains claude_cli:haiku,gemini_cli:gemini-2.5-flash
```

## What Cody (this repo's operator) should do

1. Clean up experiment code for public consumption
2. Write a proper README.md with paper abstract
3. Create reproducible experiment scripts with clear documentation
4. Add a web viewer for session reports (optional)
5. Ensure all experiment data is included and reproducible
6. Do NOT expose: GRAND_PLAN, design decisions log, authority boundaries, living creatures

## Architecture (simplified for this repo)

```
Creature = Organism(blocks=[Engine, Memory, Emotion, Immune, ...])
         + Habitat (local folder with SELF.md, bonds/, skills/)
         + Brain (Claude CLI or Gemini CLI via subprocess)

Field = Environment where creatures experience events
      Wilderness: event-driven (challenges, cooperation, discovery)
      Agora: free conversation between creatures

Experiment = seed-controlled Wilderness runs
           comparing conditions (experienced vs fresh, solo vs duo)
```

## Design decisions referenced (from Ludex, not published here)

- D-002: Brain-agnostic — any LLM works
- D-018: Brain-agnostic skills
- D-021: SELF.md emerges from reflection
- D-022: Bonds — structured relationship memory
- D-025: Creature-first design — fields serve creatures, humans observe
- D-026: Memory hygiene — dedup, source tracking, progressive disclosure
