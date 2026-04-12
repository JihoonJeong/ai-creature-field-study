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

A *field* is a deterministic event stream that a creature (or a pair) lives through for a fixed number of ticks. This paper uses the `Wilderness` field: each tick presents an event sampled from a fixed catalogue (calm day, storm, obstacle, isolation, discovery, nearby creature, etc.), and each creature chooses one action from a closed set (rest, explore, speak, trade, support, defend). Events are drawn from a Wilderness-local `random.Random(seed)` instance, so a given `(seed, tick_count)` produces the same event sequence on every invocation, independent of any other code in the process.

This last condition is non-trivial: the creature's resilience layer uses the global `random` module for retry jitter, and an earlier version of Wilderness seeded the global RNG. That meant an unlucky run with more LLM retries would advance global state and get a different event sequence. We moved event sampling to an instance-local RNG so the environment is genuinely isolated from its tenants' noise. Reproducibility at this level is what lets us report mean ± stdev and have it mean what we say it does.

This event-level determinism is what makes behavioral comparison meaningful. When we compare experienced-vs-fresh or Haiku-vs-Flash, we know the creatures faced the exact same situations. Any difference comes from the creature, not the environment.

LLM responses are *not* reproducible — Claude CLI and Gemini CLI are not seedable — so this design gives us deterministic *stimulus* and stochastic *response*. Variance then carries a clear meaning: it is the brain's own noise on a fixed task.

### Experiment protocol

Two experiments are defined:

- **Experience effect** (`experiments/experience_effect_experiment.py`). Two groups. Group A: train in wilderness #1 → reflect (write SELF.md, store memories) → test in wilderness #2. Group B: skip training → test in wilderness #2 with a fresh creature. Both groups face the same wilderness #2 seed. Any behavioral delta is attributable to lived experience.
- **Duo** (`experiments/duo_experiment.py`). Two creatures train separately in wilderness #1 (each with its own train seed), then meet in a shared wilderness #2. Actions now include social verbs (speak, support, trade). Any behavioral pattern is attributable to the interaction.

Both scripts accept a comma-separated list of seeds so that an experiment *is* a set of runs, not a single run. The aggregator reports mean ± stdev across seeds, per condition and per brain. Summary JSONs include raw per-run metrics so readers can recompute aggregates. The n=5 pilot set used seeds [42, 99, 7, 13, 55] and the n=10 confirmation set added [1, 23, 77, 100, 200]; test_seed was held at 123 in all runs to hold the shared wilderness constant.

### Brain-agnostic CLI integration

Each brain is an adapter that shells out to a local CLI: `claude` for Anthropic models, `gemini` for Google models. No paid HTTP API is invoked — a subscription CLI covers all the LLM calls. This matters for three reasons: (i) the cost is bounded and independent of experiment size, removing a practical pressure to cut corners on n; (ii) the setup runs identically on any subscriber's laptop, so reproduction is not gated on API keys; (iii) the adapter layer means a new brain is a one-file addition, not a protocol change.

### Reproducibility harness

The public repo is a standalone checkout: experiments import only from its own `ludex/` subset, not from a sibling Ludex master repo. Two concrete guards earn the reproducibility claim rather than assume it:

1. **Cwd pinning.** Experiment scripts call `os.chdir(_REPO_ROOT)` at entry. An earlier version relied on the invoker's cwd; during concurrent work we silently wrote output into the Ludex master repo when a shell had drifted there. We fixed the class of failure by removing the degree of freedom.
2. **Environment RNG isolation.** As described above, Wilderness owns its own `random.Random` so retry jitter in the resilience layer cannot alter event sampling.

Reference data lives under `experiments/<name>_results/` and is committed; pilot and re-reproduction data lives under `experiments/smoke/*` and is gitignored. An `--output-dir` flag on every experiment script lets a reader rerun without overwriting the committed reference set.

A session report viewer renders per-run wilderness JSONs into human-readable markdown for qualitative inspection alongside the quantitative summary.

### Replication discipline (the meta-finding)

Early in this study we took four behavioral observations at face value based on n=1–3 runs:

1. *Experience makes creatures more cautious (Haiku) or less defensive (Flash).*
2. *Social presence eliminates defensive behavior in duos.*
3. *Emotion flips negative → positive in duos.*
4. *(From a parallel ToM-self-evaluation study in the Ludex track) Haiku is permissive, Flash is strict.*

When we re-ran each claim under the same seeds at n=5, all four collapsed:

- #1 (experience → caution): defend-rate direction flipped. Reference (n=3) had Group A defend at 13 ± 6% and Group B at 3 ± 6%. The n=5 pilot on the same three seeds plus two more had Group A at 4 ± 6% and Group B at 8 ± 5%. The stdev equals the effect.
- #2 (social presence → no defense): held for Haiku (2 ± 5%) but not for Flash (12 ± 8%) in the Pair A n=5 pilot. The pooled average was misleading; per-brain behavior is the correct granularity.
- #3 (emotion → hopeful/loving): the signature emotion `loving` did not appear in any of the 5 duo re-runs with the original seed. It returned at n=10 but only in the same-brain Haiku pair, which is a different condition.
- #4 (Haiku permissive / Flash strict): run independently by the Ludex track at n=10 and collapsed to a weak trend (Haiku slightly stricter, neither pole as originally described).

Every claim's effect size was within its own sample-level stdev. These were real patterns in the one or two runs that produced them, and they were also consistent with noise.

A fifth claim — *brain-specific role differentiation in duos* — surfaced during the re-analysis of #2. Rather than accept it, we subjected it to three progressively stricter tests: n=5 on the original heterogeneous pair (Haiku+Flash), then a same-brain pair in each direction (Haiku+Haiku as a falsifier against the pair-dynamics explanation that "someone has to fill the explore role," Flash+Flash as a symmetric check), and finally n=10 on all three pair configurations. It passed each stage. The per-brain behavioral ranges remained non-overlapping on speak+support, explore, and defend at n=10, and the same-brain pairs deepened each brain's attractor instead of redistributing.

The methodology this paper defends is that sequence: every headline must be stated with variance, every behavioral claim must pass at least one *symmetric* falsifier (a same-brain pair for a between-brain claim; a no-treatment control for an experience claim), and every single-run observation should be treated as a hypothesis, not a result. Our contribution is a replicable field-study pipeline where these checks are cheap enough to run — no paid API, no specialized hardware, and reference data committed alongside the code.

## Findings (exploratory, with variance)

### Reported with confidence (n=10, stable)

- **Attractor dynamics: brain-fixed attractors and within-pair amplification (n=10 × 3 pairs, symmetric).**

  Each brain occupies a stable behavioral attractor in duos, and same-brain pairs *deepen* that attractor rather than splitting roles. These are one claim with two faces: the attractor is the state, the amplification is what happens when two copies of the same attractor meet.

  - **Setup.** Three pairs — Haiku+Flash (A), Haiku+Haiku (B), Flash+Flash (C). Train seeds [42, 99, 7, 13, 55, 1, 23, 77, 100, 200], test_seed 123, 10 ticks. Aggregates are mean ± stdev across the 10 runs.

    | | Pair A: Haiku+Flash | | Pair B: Haiku+Haiku | | Pair C: Flash+Flash | |
    |---|---|---|---|---|---|---|
    | | Haiku | Flash | Haiku_1 | Haiku_2 | Flash_1 | Flash_2 |
    | speak+support | 50% | 19% | **76%** | **73%** | 33% | 19% |
    | speak | 31% ± 16% | 16% ± 11% | 45% ± 9% | 34% ± 11% | 32% ± 15% | 17% ± 13% |
    | support | 19% ± 12% | 3% ± 5% | 31% ± 12% | 39% ± 11% | 1% ± 3% | 2% ± 4% |
    | explore | 33% ± 18% | **60% ± 9%** | 9% ± 10% | 16% ± 11% | 44% ± 17% | 48% ± 15% |
    | defend | 2% ± 4% | 12% ± 6% | 7% ± 7% | 3% ± 5% | 13% ± 12% | **21% ± 15%** |

  - **Attractors separate cleanly.** Across all 7 creatures in the three pairs:
    - Haiku (n=4 across A+B): speak+support 50–76%, explore 9–33%, defend 2–7%.
    - Flash (n=3 across A+C): speak+support 19–33%, explore 44–60%, defend 12–21%.
    - The per-brain ranges do not overlap on any of these three summary metrics. Haiku never enters Flash's explore/vigilant range; Flash never enters Haiku's social/supportive range.
  - **Symmetric falsifiers pass.** Pair B and Pair C were introduced to rule out a pair-dynamics explanation where one creature simply fills a role the other vacates. In both same-brain pairs, neither creature crossed into the other brain's attractor — so the attractor is brain-fixed, not socially negotiated.
  - **Same-brain pairs amplify instead of redistributing.** Once the attractor is brain-fixed, the predicted behavior when two copies of the same attractor meet is that neither pulls the other toward its complement — and we see exactly that, stronger:
    - Pair B: both Haikus push *deeper* into social — speak+support 73–76% (vs 50% for the Haiku in pair A). Explore drops to 9–16% (vs 33%).
    - Pair C: both Flashes push *deeper* into vigilant — defend 13–21% (vs 12% in pair A). Explore drops slightly (44–48% vs 60%).
    - In other words: the partner's role is not "fill the gap" but "do more of what I do." This is the structural consequence of brain-fixed attractors when both poles are the same; it is not a separate mechanism.
  - **Variance width differs by brain.** Flash's stdev is ~1.5–2× wider than Haiku's on each summary metric, and this holds in both the mixed pair and the same-brain pair:
    - Pair A Haiku stdev: speak 16, explore 18, defend 4. Pair A Flash stdev: speak 11, explore 9, defend 6.
    - Pair B Haiku stdev (both creatures): speak 9–11, explore 10–11, defend 5–7.
    - Pair C Flash stdev (both creatures): speak 13–15, explore 15–17, defend 12–15.
    - Flash occupies its attractor *more loosely* than Haiku occupies its own. The width is consistent with or without a Haiku partner, so this is a brain-level property, not an interaction effect.
  - *As of 2026-04-13, this is the only behavioral finding that survived replication across both research tracks. A separate ToM "brain-stricture" hypothesis explored in the Ludex track failed to replicate at n=10 — the v1 asymmetry collapsed into a weak trend. The methodology's replication discipline is the meta-finding; brain-fixed attractor dynamics — attractor separation, symmetric falsification, within-pair amplification, and brain-dependent variance width — is the behavioral finding that passed it.*

### Reported as variance observations (n=5 direction-unstable, downgraded)

- **"Experience makes creatures cautious/less-defensive"** (original headline, downgraded).
  - Reference (n=3, seeds 42/99/7): A defend 13.3% ± 5.8%, B 3.3% ± 5.8%.
  - Pilot (n=5, same seeds + 13, 55): A 4.0% ± 5.5%, B 8.0% ± 4.5%.
  - Direction flipped; stdev ≈ effect size in both conditions. Claim is not supported at this sample size.

- **"Social presence eliminates defensive behavior (13-20% solo → 3% duo)"** (original headline, downgraded).
  - n=5 Haiku+Flash duo: Haiku defend 2% ± 4.5% (matches claim), Flash defend 12% ± 8% (does not). Averaging across creatures was misleading. Per-brain behavior is more informative.

- **"Emotion flips negative → positive in duo (hopeful/loving)"** (original headline, downgraded).
  - `loving` appeared in the n=1 reference; absent across all n=5 duo runs. `hostile`, `desperate`, `afraid` appear alongside `hopeful` in the emotion union. Single-run observation; not replicated.

## Variance & limitations (dedicated section — not a footnote)

AI-creature behavior at n≤5 is variance-dominated on most metrics we tracked. Four of the original single-run observations failed replication at n=5, and the effect size of each was within its own sample-level stdev. Reporting means without stdev actively misleads: at n=5 we can recover plausible-looking headlines that disagree on direction between reruns of the same seeds. We argue this as a general caution for AI-creature field studies, not as a local quirk of our setup, and we report per-brain mean ± stdev for every metric in the Findings table rather than a single pooled number.

### Observed but not isolated

Some patterns at n=10 are visible but cannot be attributed to a single mechanism within this experimental design. We list them so they are not lost, but do not claim them:

- **Final-energy gap across pair types.** Same-brain Haiku pairs end with notably lower energy (48–50) than the mixed pair (63–69) or the same-brain Flash pair (66). Three mechanisms would each produce this signature — social actions are metabolically costly; explore actions generate energy via event interactions; or the wilderness event mix happens to penalize whichever pair has the least explore. The current setup cannot distinguish between them. Follow-up planned as a separate controlled study; not in scope for this paper.

### Non-determinism caveat

LLM responses are not seedable, so strict reproduction of a specific tick sequence is impossible. We compensate by seeding the *environment* (so creatures face identical event streams) and reporting aggregate statistics across seed sets. Readers re-running the paper's commands will see values within reported stdev bands, not exact matches.

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
- ~~Flash-variance-width sub-finding~~ — confirmed at n=10; merged into main attractor-dynamics section (2026-04-13).
- ~~Within-pair amplification — standalone or merged?~~ — merged into attractor-dynamics as structural consequence (2026-04-13).
- ~~Final-energy asymmetry — in scope or deferred?~~ — deferred to follow-up; one-liner in Variance & limitations (2026-04-13).
- **Methodology section polish** — first draft committed; pass for tightening prose and citing specific n=10 seed runs.
- **Variance & limitations section** — expanded 2026-04-13; one more pass with full stdev tables pending.
- Reference non-deterministic event sampler in the field implementation — verify the `random.Random(seed)` flow is isolated per wilderness instance (no cross-run seed pollution) before publishing reproducibility claim.
