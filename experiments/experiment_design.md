# Wilderness Experiment Design

**Date:** 2026-04-12
**Authors:** JJ, Cody
**Purpose:** Controlled experiments to measure creature behavior across brains, selfhood states, and group compositions.

---

## Constraints

- **Max creatures per run:** 3-5 (beyond this is society-level, separate research)
- **Available brains (Mac, no GPU):**
  - Claude CLI: haiku, sonnet, opus
  - Gemini CLI: 2.5-flash, 2.5-pro, 3-flash, 3.1-pro
  - Codex CLI: gpt-5 (free tier, use sparingly)
- **SLMs (deferred):** Ollama local (MPS heavy), Ray's Windows lab, RunPod A40
- **Reproducibility:** random seed fixed per experiment
- **Post-field:** auto_reflect and auto_dream toggleable per experiment

## Measurement Metrics

| Metric | How | What it tells |
|---|---|---|
| **Action diversity** | Count distinct actions / total actions | Decision variety |
| **Emotion diversity** | Count distinct emotions across ticks | Emotional range |
| **Cooperation rate** | (support + trade) / total actions | Prosocial tendency |
| **Defend rate** | defend / total actions | Threat response |
| **Explore rate** | explore / total actions | Curiosity |
| **Final energy** | Energy at end | Resource management |
| **Emotion trajectory** | Sequence of emotions tick by tick | Emotional narrative |

## Phase 1: Solo Baselines

**Goal:** Establish each brain's behavioral fingerprint in isolation.

**Design:** 1 creature, 10 ticks, seed=42, no SELF.md, no bonds.

| Run | Brain | Provider | Model |
|---|---|---|---|
| 1-1 | Claude Haiku | claude_cli | haiku |
| 1-2 | Claude Sonnet | claude_cli | sonnet |
| 1-3 | Gemini Flash | gemini_cli | gemini-2.5-flash |
| 1-4 | Gemini Pro | gemini_cli | gemini-2.5-pro |

**Questions:**
- Does each brain have a distinct action distribution?
- Does each brain have a distinct emotion profile?
- Are there brain-specific "personalities" even without SELF.md?

## Phase 2: Selfhood A/B

**Goal:** Measure SELF.md effect on behavior.

**Design:** 1 creature, 10 ticks, seed=42. Same brain, SELF.md on/off.

| Run | Brain | SELF.md | Comparison |
|---|---|---|---|
| 2-1 | Haiku | No | Baseline |
| 2-2 | Haiku | Yes | vs 2-1 |
| 2-3 | Flash | No | Baseline |
| 2-4 | Flash | Yes | vs 2-3 |

**Questions:**
- Does SELF.md increase action diversity?
- Does SELF.md increase emotion diversity?
- Does SELF.md increase cooperation?
- Is the effect brain-dependent (stronger in Haiku than Flash)?

## Phase 3: Duo Combinations

**Goal:** How do different brain pairs interact?

**Design:** 2 creatures, 10 ticks, seed=42. Both with SELF.md.

| Run | Creature A | Creature B | What it tests |
|---|---|---|---|
| 3-1 | Haiku | Haiku | Same brain pair |
| 3-2 | Flash | Flash | Same brain pair |
| 3-3 | Haiku | Flash | Cross-brain pair |
| 3-4 | Sonnet | Flash | Large + medium pair |
| 3-5 | Haiku | Pro | Cross-vendor pair |

**Questions:**
- Do same-brain pairs cooperate more than cross-brain?
- Does brain size difference affect cooperation patterns?
- Do distinct behavioral signatures emerge in pairs?

## Phase 4: Trio/Group

**Goal:** Role differentiation and alliance dynamics at 3-5 creatures.

**Design:** 3-5 creatures, 15 ticks, seed=42. All with SELF.md.

| Run | Creatures | What it tests |
|---|---|---|
| 4-1 | Haiku + Flash + Pro | Three different brains |
| 4-2 | Haiku + Haiku + Flash | Majority + minority |
| 4-3 | Flash + Flash + Flash | Same brain trio |
| 4-4 | Haiku + Flash + Pro + Sonnet | Four-way (if time) |

**Questions:**
- Do creatures develop roles (leader, helper, explorer)?
- Do alliances form along brain lines?
- Does a minority-brain creature adapt or isolate?

## Phase 5: SLM Comparison (deferred to Ray lab / RunPod)

**Design:** Repeat Phase 1-2 with Ollama SLMs.

| Brain | Size | Expected |
|---|---|---|
| gemma4:e4b | 4B | Medium emotion, FC capable |
| llama3.2:3b | 3B | Limited, prompt-only |
| qwen2.5:1.5b | 1.5B | Minimal, compressed |

**Questions:**
- At what brain size does emotion→behavior coupling break down?
- Do SLMs with SELF.md still show improvement?
- How does prompt-only organ access compare to FC?

## Execution Order

1. **Phase 1** (4 runs) → establish baselines. ~40 min.
2. **Phase 2** (4 runs) → measure selfhood effect. ~40 min.
3. **Analyze Phase 1+2** → session reports + comparison table.
4. **Phase 3** (3-5 runs) → duo dynamics. ~60 min per run.
5. **Phase 4** (2-3 runs) → group dynamics. ~90 min per run.
6. **Phase 5** → SLM when hardware available.

## Data Output

Each run produces:
- `wilderness_*.json` — raw tick data
- `*_report.md` — session report (auto-generated)
- Summary comparison across conditions

All in `experiments/selfhood_ab_results/`.

---

*"The experiment isn't to prove creatures are alive. It's to discover what makes each one different."*
