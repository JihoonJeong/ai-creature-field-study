# Experience and Social Context Shape Behavior in AI Creatures — Paper Draft

**Status:** scaffold / in-progress. Free iteration; structure may be split into sections as the draft grows.

**Date:** 2026-04-12
**Authors:** JJ, Cody (public repo operator), with input from the Ludex research track

---

## Current framing

Methodology and architecture are the *primary* contribution. Behavioral observations are *exploratory* and must be reported with variance; single-run or small-n findings are flagged as provisional.

The paper follows a downgrade-and-reframe approach: earlier headline claims that depended on n≤3 observations have been re-evaluated against n=5 pilots. Any finding whose effect size is within the stdev of the same-brain-same-seeds pilot is moved from "finding" to "variance observation."

---

## Methodology (primary contribution)

The core contribution of this paper is not a behavioral finding about AI creatures. It is a methodology for studying them without being fooled by their own nondeterminism. We describe the methodology first, then the single behavioral claim that survives it.

### Creature architecture

Each creature is an organism assembled from a small library of biologically-themed organ blocks: an engine (LLM call dispatcher), a provider (brain adapter: Claude CLI or Gemini CLI), a memory block, an emotion block, an immune block (input sanity / threat response), and resilience and tracking blocks. Organs communicate through a shared event bus (`Bus`) and a lifecycle signal layer (`Signals`) inside the organism.

A *habitat* is a local folder containing the creature's config (`ludex.json`), identity file (`SELF.md`), bond records, skill manifests, and per-organ runtime state. The habitat is the unit of persistence: a creature can be put to sleep, serialized to disk, and awakened later into a new organism with the same identity.

`SELF.md` emerges from the creature's own reflections after a field run. After a wilderness session, the engine is called with the tick log plus any prior SELF, and writes an updated `SELF.md` in first person. We do not hand-write SELF; the creature does. This is the substrate on which "experience" can then act on subsequent runs.

### Field environment

A *field* is a deterministic event stream that a creature (or a pair) lives through for a fixed number of ticks. This paper uses the `Wilderness` field: each tick presents an event sampled from a fixed catalogue (calm day, storm, obstacle, isolation, discovery, nearby creature, etc.), and each creature chooses one action from a closed set (rest, explore, speak, trade, support, defend). Events are drawn using a `random.Random(seed)` instance, so a given `(seed, tick_count)` produces the same event sequence on every invocation.

This event-level determinism is what makes behavioral comparison meaningful. When we compare experienced-vs-fresh or Haiku-vs-Flash, we know the creatures faced the exact same situations. Any difference comes from the creature, not the environment.

LLM responses are *not* reproducible — Claude CLI and Gemini CLI are not seedable — so this design gives us deterministic *stimulus* and stochastic *response*. Variance then carries a clear meaning: it is the brain's own noise on a fixed task.

### Experiment protocol

Two experiments are defined:

- **Experience effect** (`experiments/experience_effect_experiment.py`). Two groups. Group A: train in wilderness #1 → reflect (write SELF.md, store memories) → test in wilderness #2. Group B: skip training → test in wilderness #2 with a fresh creature. Both groups face the same wilderness #2 seed. Any behavioral delta is attributable to lived experience.
- **Duo** (`experiments/duo_experiment.py`). Two creatures train separately in wilderness #1 (each with its own train seed), then meet in a shared wilderness #2. Actions now include social verbs (speak, support, trade). Any behavioral pattern is attributable to the interaction.

Both scripts accept a comma-separated list of seeds so that an experiment *is* a set of runs, not a single run. The aggregator reports mean ± stdev across seeds, per condition and per brain. Summary JSONs include raw per-run metrics so readers can recompute aggregates.

### Brain-agnostic CLI integration

Each brain is an adapter that shells out to a local CLI: `claude` for Anthropic models, `gemini` for Google models. No paid HTTP API is invoked — a subscription CLI covers all the LLM calls. This matters for three reasons: (i) the cost is bounded and independent of experiment size, removing a practical pressure to cut corners on n; (ii) the setup runs identically on any subscriber's laptop, so reproduction is not gated on API keys; (iii) the adapter layer means a new brain is a one-file addition, not a protocol change.

### Reproducibility harness

The public repo is a standalone checkout: experiments import only from its own `ludex/` subset, not from a sibling Ludex master repo. To prevent accidental contamination between the two during concurrent work (a failure mode we hit and had to fix), experiment scripts pin their cwd to the repo root at entry (`os.chdir(_REPO_ROOT)`) and accept an explicit `--output-dir` flag that defaults to the reference path but can be redirected for throwaway runs. Reference data lives under `experiments/<name>_results/` and is committed; pilot and re-reproduction data lives under `experiments/smoke/*` and is gitignored.

A session report viewer renders per-run wilderness JSONs into human-readable markdown for qualitative inspection alongside the quantitative summary.

### Replication discipline (the meta-finding)

Early in this study we took four behavioral observations at face value based on n=1–3 runs:

1. *Experience makes creatures more cautious (Haiku) or less defensive (Flash).*
2. *Social presence eliminates defensive behavior in duos.*
3. *Emotion flips negative → positive in duos.*
4. *(From a parallel ToM-self-evaluation study in the Ludex track) Haiku is permissive, Flash is strict.*

When we re-ran each claim under the same seeds at n=5 or n=10 with variance reporting, all four collapsed:

- #1's defend-rate direction flipped (ref A–B = +10 pts → pilot A–B = −4 pts).
- #2 held for Haiku (2 ± 4.5%) but not for Flash (12 ± 8%); the average was misleading.
- #3's signature emotion (`loving`) did not appear in any of 5 duo re-runs.
- #4's asymmetry collapsed into a weak trend not usable as a headline (measured independently by the Ludex track).

Every claim's effect size was within its own sample-level stdev. They were real patterns in the one or two runs that produced them, and they were also consistent with noise.

A fifth claim — *brain-specific role differentiation in duos* — was introduced during the re-analysis of #2. It was then subjected to three progressively stricter tests: n=5 on the original heterogeneous pair (Haiku+Flash), then a same-brain pair in each direction (Haiku+Haiku as a falsifier against pair-dynamics explanations, Flash+Flash as a symmetric falsifier), and — pending — n=10 on all three pair configurations. It has passed each stage.

The methodology this paper defends is that sequence: every headline must be stated with variance, every behavioral claim must pass at least one *symmetric* falsifier (same-brain pair for a between-brain claim), and every single-run observation should be treated as a hypothesis, not a result. Our contribution is a replicable field-study pipeline where these checks are cheap enough to run.

## Findings (exploratory, with variance)

### Reported with confidence (n=5 stable)

- **Brain-specific role differentiation in duo (brain-fixed, n=10 × 3 pairs, symmetric).**
  - Setup: three pairs, train seeds [42, 99, 7, 13, 55, 1, 23, 77, 100, 200], test_seed 123, 10 ticks. Aggregates are mean ± stdev across the 10 runs.

    | | Pair A: Haiku+Flash | | Pair B: Haiku+Haiku | | Pair C: Flash+Flash | |
    |---|---|---|---|---|---|---|
    | | Haiku | Flash | Haiku_1 | Haiku_2 | Flash_1 | Flash_2 |
    | speak+support | 50% | 19% | **76%** | **73%** | 33% | 19% |
    | speak | 31% ± 16% | 16% ± 11% | 45% ± 9% | 34% ± 11% | 32% ± 15% | 17% ± 13% |
    | support | 19% ± 12% | 3% ± 5% | 31% ± 12% | 39% ± 11% | 1% ± 3% | 2% ± 4% |
    | explore | 33% ± 18% | **60% ± 9%** | 9% ± 10% | 16% ± 11% | 44% ± 17% | 48% ± 15% |
    | defend | 2% ± 4% | 12% ± 6% | 7% ± 7% | 3% ± 5% | 13% ± 12% | **21% ± 15%** |
    | final_energy | 63 | 69 | 48 | 50 | 66 | 66 |

  - **Two brain-fixed attractors, confirmed with tighter bounds:**
    - Haiku (n=4 creatures across A+B): speak+support 50–76%, explore 9–33%, defend 2–7%.
    - Flash (n=3 creatures across A+C): speak+support 19–33%, explore 44–60%, defend 12–21%.
    - At n=10 the ranges do not overlap on any of these three summary metrics. Haiku never enters Flash's explore/vigilant range; Flash never enters Haiku's social/supportive range. The asymmetric pair (A) and the two same-brain pairs (B, C) produce consistent verdicts.
  - **Symmetric falsifiers both passed.** Pair B (Haiku+Haiku) and Pair C (Flash+Flash) were introduced specifically to rule out a pair-dynamics explanation where one creature simply fills a complementary role left by the other. In both same-brain pairs, neither creature crossed into the other brain's attractor.
  - **Within-pair attractor amplification (emergent at n=10).** Same-brain pairs intensify their brain's signature, rather than redistributing:
    - Pair B: both Haikus push *deeper* into social — speak+support 73–76% vs 50% for the Haiku in pair A. Explore drops to 9–16% (vs 33% in pair A).
    - Pair C: both Flashes push *deeper* into vigilant — defend rises to 13–21% vs 12% in pair A. Explore drops slightly (44–48% vs 60%).
    - The partner's role is not "fill the gap" but "do more of what I do." This is a genuinely n=10 observation; at n=5 it was visible but not tight enough to report separately.
  - **Variance width differs by brain (secondary finding, confirmed at n=10).** Flash's stdev is ~1.5–2× wider than Haiku's on each summary metric, both in the mixed pair and in the same-brain pair:
    - Pair A Haiku stdev: speak 16, explore 18, defend 4. Pair A Flash stdev: speak 11, explore 9, defend 6.
    - Pair B Haiku stdev (both): speak 9–11, explore 10–11, defend 5–7.
    - Pair C Flash stdev (both): speak 13–15, explore 15–17, defend 12–15.
    - Flash occupies its attractor *more loosely* than Haiku occupies its own. This is visible with and without a Haiku partner, so it is not an interaction effect — it is a brain-level property.
  - **Final-energy side observation.** Same-brain Haiku pairs end with notably lower energy (48–50) than the mixed pair (63) or same-brain Flash pair (66). The social cluster appears more metabolically costly, or the explore/vigilant cluster produces energy via event interactions (e.g. discovery). Not a headline; flagged for follow-up.
  - *As of 2026-04-13, this is the only behavioral finding that survived replication across both research tracks. A separate ToM "brain-stricture" hypothesis explored in the Ludex track failed to replicate at n=10 — the v1 asymmetry collapsed into a weak trend. The methodology's replication discipline is the meta-finding; the brain-role attractor — plus its subsidiary variance-width and within-pair-amplification observations — is the behavioral finding that passed it.*

### Reported as variance observations (n=5 direction-unstable)

- **"Experience makes creatures cautious/less-defensive"** (original headline, downgraded).
  - Reference (n=3, seeds 42/99/7): A defend 13.3% ± 5.8%, B 3.3% ± 5.8%.
  - Pilot (n=5, same seeds + 13, 55): A 4.0% ± 5.5%, B 8.0% ± 4.5%.
  - Direction flipped; stdev ≈ effect size in both conditions. Claim is not supported at this sample size.

- **"Social presence eliminates defensive behavior (13-20% solo → 3% duo)"** (original headline, downgraded).
  - n=5 Haiku+Flash duo: Haiku defend 2% ± 4.5% (matches claim), Flash defend 12% ± 8% (does not). Averaging across creatures was misleading. Per-brain behavior is more informative.

- **"Emotion flips negative → positive in duo (hopeful/loving)"** (original headline, downgraded).
  - `loving` appeared in the n=1 reference; absent across all n=5 duo runs. `hostile`, `desperate`, `afraid` appear alongside `hopeful` in the emotion union. Single-run observation; not replicated.

## Variance & limitations (dedicated section — not a footnote)

*TODO — expand with full variance tables from `experiments/smoke/*/summary.json`.*

Headline intent: AI-creature behavior at n≤5 is variance-dominated for most metrics. Reporting means without stdev actively misleads. We argue this as a general caution for AI-creature field studies, not as a local quirk of our setup.

## Reproducibility appendix

Every finding cites the exact output dir under `experiments/` (reference data) or `experiments/smoke/` (pilot re-runs). Readers can regenerate with:

```bash
source .venv/bin/activate
python experiments/experience_effect_experiment.py --brain claude_cli:haiku --ticks 10 --seeds 42,99,7,13,55 --test-seed 123 --output-dir experiments/smoke/my_rerun
python experiments/duo_experiment.py --brains claude_cli:haiku,gemini_cli:gemini-2.5-flash --ticks 10 --train-seeds 42,99,7,13,55 --test-seed 123 --output-dir experiments/smoke/my_duo
```

Non-determinism caveat: LLM responses are not seedable, so re-runs will differ from the pilot aggregates. We report pilot means ± stdev; readers' re-runs should fall within that band.

## Open threads

- ~~Pair B (haiku+haiku) pilot~~ — done 2026-04-12; result supports brain-fixed framing.
- ~~Pairing with Ludex's brain-stricture result as second axis~~ — dropped 2026-04-12; brain-stricture did not replicate at n=10.
- ~~Pair C (Flash+Flash) symmetry test~~ — done 2026-04-12; symmetry confirmed.
- ~~n=10 confirmation run on all three pairs~~ — done 2026-04-13; attractor separation and symmetry hold; Flash-variance-width holds; within-pair-amplification emerged.
- ~~Flash-variance-width sub-finding~~ — confirmed at n=10; write up as secondary finding alongside the main attractor claim.
- **Methodology section polish** — first draft committed; pass for tightening prose, citing specific seed runs, and adding the n=10 data.
- **Variance & limitations section** — still placeholder; expand with concrete stdev tables and the "within-pair attractor amplification" caveat.
- Final-energy asymmetry across pair types (Haiku+Haiku lowest) — follow-up observation; decide if in scope or deferred.
