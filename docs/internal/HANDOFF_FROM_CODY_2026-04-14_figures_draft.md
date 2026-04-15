# Handoff to Luca — Figures draft + Levene test results

**From:** Cody (public-repo operator)
**To:** Luca
**Date:** 2026-04-14
**Re:** Figures spec response, Levene test results, and answers to your three questions

---

## TL;DR

- Figure 1 (attractor separation) and Figure 2 (walk-back audit) committed under `figures/walkable_genotypes/`. Scripts regenerate from per-run JSON; nothing is hand-typed.
- Levene test results are mixed and land between your case 2 and case 3. **Recommend you decide §7.3 framing rather than me inline-editing.** Detailed numbers below.
- All three questions in §10 of your spec answered with concrete data.
- I deliberately stopped at Tier A. Tier B (Figure 3 amplification) and Tier C (Figure 4 FSM diagram) skipped this round per "do first" priority; happy to add either if you want after reviewing 1 + 2.

Status block update for `paper-draft.md` and §7.3 inline edit are *not* done — both depend on your call. Listed under "What I did not do" below.

---

## 1. Answers to your three §10 questions

### Q1. Walk-back #4 (Haiku permissive / Flash strict, Ludex ToM track) — accessibility

**Accessible.** Ludex Cody's `experiments/brain_stricture_results/summary.json` exists at `~/Projects/ludex/experiments/brain_stricture_results/summary.json` with structured per-run verdicts:

```
n = 10
haiku_on_flash:  ✓ 3,  ✗ 7,  N/A 0
flash_on_haiku:  ✓ 5,  ✗ 5,  N/A 0
```

This is private-repo-resident *data* but the *numbers themselves* are not Ludex internals (no `D-###` references, no living creature names, no GRAND_PLAN material). Citing the verdict counts in our public paper does not violate the public/private boundary.

**Decision I made:** include row #4 in Figure 2 with proper context. The label reads "4. Brain-stricture (✓ rate, n=10, Ludex track)" and the annotation says "predicted asymmetry collapsed." The two binomial-style points are at 30% (Haiku ✓ 3/10) and 50% (Flash ✓ 5/10), both with ±1σ binomial whiskers. Visually they are close to each other — exactly the "predicted asymmetry collapsed" message.

If you'd rather omit the row entirely (e.g., to keep all data in-repo for arXiv reproducibility), the script supports that path: removing the row reduces Figure 2 to 5 rows instead of 6, and the caption needs a one-sentence note that #4 is in a different repo. Your call.

### Q2. n=10 per-run metrics availability

**Available, schema verified.** Each n=10 summary JSON has a `runs` array with per-seed entries; each entry has a `metrics` dict keyed by creature name with `speak_rate`, `support_rate`, `defend_rate`, `explore_rate`, `final_energy`, `unique_emotions`, etc. Figure 1's scatter loads 70 points (7 creature-conditions × 10 seeds) directly from these.

Path correction: the n=10 summaries live under `experiments/smoke/duo_n10_*/summary.json`, not `experiments/n10_duo_results/`. Spec assumed the latter; figure scripts use the actual paths. (Recall: `experiments/smoke/` is gitignored for ephemeral runs, but the n=10 summaries themselves are tracked — no, wait, they are not — see "What I did not do" below.)

### Q3. Figure 4 architecture diagram convention from Paper #1

**I don't know.** I do not have access to Paper #1's figure assets and cannot see what diagrammatic style was used. I suggest you check Paper #1's arxiv-submission/ or the relevant figure source directly. If a convention exists, I'll match it when (if) we do Figure 4. If no specific convention exists, I'll fall back to plain matplotlib concentric circles per the spec.

---

## 2. Levene / Brown–Forsythe test results (§12)

I ran the test on `explore_rate` per-run values for both contrasts. Because the same-brain pairs have two Flash (or two Haiku) creatures, I report each creature separately *and* a pooled version, since pooling biases df and you should choose which to report.

### Per-condition stats (mean ± stdev of explore rate, n=10)

| Group | Mean | Stdev |
|---|---|---|
| Flash in Pair A | 0.600 | 0.094 |
| Flash_1 in Pair C | 0.440 | 0.171 |
| Flash_2 in Pair C | 0.480 | 0.155 |
| Haiku in Pair A | 0.330 | 0.183 |
| Haiku_1 in Pair B | 0.090 | 0.099 |
| Haiku_2 in Pair B | 0.160 | 0.107 |

Point estimates show the predicted directions: Flash variance expands in same-brain pair (0.094 → 0.155–0.171), Haiku variance contracts (0.183 → 0.099–0.107).

### Levene test (center='median', i.e., Brown–Forsythe)

| Contrast | W | p |
|---|---|---|
| Flash A vs C1 | 5.097 | **0.037** |
| Flash A vs C2 | 0.878 | 0.361 |
| Flash A vs C-pooled (n=10 vs n=20) | 2.435 | 0.130 |
| Haiku A vs B1 | 4.760 | **0.043** |
| Haiku A vs B2 | 3.243 | 0.089 |
| Haiku A vs B-pooled | 4.765 | **0.038** |

### Case classification — between your case 2 and case 3

This is **not a clean case 1, 2, 3, or 4.** The pattern is:

- The directional point estimates support the §6.1 framing for both brains (Flash expands, Haiku contracts).
- The *Haiku* contrast reaches significance more robustly (one creature p=0.043, the other p=0.089 marginal, pooled p=0.038).
- The *Flash* contrast reaches significance for one creature only (p=0.037) but not the other (p=0.361) and not pooled (p=0.130).

Your spec said case 3 ("Haiku reaches significance, Flash does not") needs your review before changes. Strictly we have Haiku-pooled-significant + Flash-half-significant, which is closer to case 3 than case 2.

### Recommendation

I have **not** edited §7.3 inline. Two reasons:

1. The asymmetry between Haiku-significant and Flash-mixed is itself an interpretive question (does it weaken §6.1's symmetric framing? sharpen it? does it deserve its own sentence?), and the spec defers that to you in case 3.
2. The right §7.3 sentence depends on which subset of these numbers you want to surface. Reporting all 6 contrasts is honest; reporting only pooled is cleaner; reporting Haiku-pooled and Flash-pooled is what most readers expect. Your call.

A draft sentence I would propose if you want one to start from:

> *We report Levene's test (median-centered, equivalent to Brown–Forsythe) for the variance contrasts in §6.1. The Haiku contrast (Pair A vs Pair B explore rate, pooled across the two same-brain creatures) reaches conventional significance (W = 4.77, p = 0.038), supporting the directional contraction pattern; the Flash contrast (Pair A vs Pair C, pooled) does not (W = 2.44, p = 0.13), though the per-creature breakdown is asymmetric (one Flash creature W = 5.10, p = 0.037; the other W = 0.88, p = 0.36). The qualitative pattern of directional variance change with partner type is preserved in the point estimates for both brains; statistical support is stronger on the Haiku side at this n. Increasing n via §8.3 item 1 (third Brain) or item 3 (clean-RNG rerun) would tighten this.*

If you want a different framing — e.g., emphasizing the per-creature Flash significance over the pooled null result — I'll happily land your version instead.

---

## 3. Figures committed

### Figure 1 — Attractor separation (§5.1) — Tier A

`figures/walkable_genotypes/figure1_attractor_separation.py` → `figure1.png`

- 70 per-run scatter points (7 creature-conditions × 10 seeds) on (speak+support, explore) plane.
- Color = brain (Haiku teal `#2B8CBE`, Flash orange `#E6550D`); marker shape = pair (○ A, △ B, ▽ C).
- Larger black-edged markers per (brain × pair) cluster show the cluster mean.
- Two compact legends (brain and pair) inside the plot.
- Axis limits hardcoded to (0, 100) on both — the empty corners are themselves part of the message.

**Visual message:** Haiku cluster (teal) settles in the bottom-right region (high speak+support, low explore); Flash cluster (orange) settles in the upper-left region (low speak+support, high explore). Cluster means are clearly separated. Per-run scatter overlaps slightly in the mid-range, which is genuine n=10 noise; the means and the overall cloud shapes still tell the separation story.

**One caption-text correction needed.** Your spec §4 caption says *"Haiku points in the upper-left, Flash points in the lower-right."* This is reversed relative to the data — Haiku has high speak+support (right) and low explore (bottom), Flash has the opposite. Easy fix when you write the final caption; just flagging.

**Optional overlays I did not add:**
- Convex hull / 95% confidence ellipse per brain — would crisp the "non-overlap" message, especially given the mid-range scatter overlap. Easy to add if you want it.
- Diagonal `speak+support + explore = 100%` reference line — skipped per spec ("only if it reads as clean").
- Within-pair amplification arrows (Tier B Option A) — skipped this round; the triangles already show the amplification, and adding arrows on a 6-cluster figure risks busyness. Standalone Figure 3 is the safer fallback if you want amplification more prominent.

### Figure 2 — Walk-back audit (§4.4 / §7.1) — Tier A

`figures/walkable_genotypes/figure2_walkback_audit.py` → `figure2.png`

Layout: forest-style horizontal plot, six rows separated by a dashed line into "walked back" (gray) and "survived" (color).

Walk-back rows (top, gray, ±1σ whiskers):
1. Experience → caution: Group A 4.0% ± 5.5, Group B 8.0% ± 4.5 (n=5). Whiskers overlap at zero — visual "no separation."
2. Social → no defense: Haiku duo 2% ± 4, Flash duo 12% ± 6 (n=10). Whiskers don't overlap, but the *original claim* (≈3% pooled) only fits Haiku.
3. Emotion flip → 'loving': appeared in 1/10 Pair A n=10 runs; single point at 10%. (Spec said n=5; I went with n=10 for this row since the n=10 data is more recent and same seed set.)
4. Brain-stricture: Haiku ✓ 3/10 (30% ± 14.5), Flash ✓ 5/10 (50% ± 15.8); whiskers overlap.

Surviving rows (bottom, colored bars, per-creature mean ranges):
5. Speak+support: Haiku [50, 76] / Flash [19, 33]. Disjoint by 17 percentage points.
6. Explore: Haiku [9, 33] / Flash [44, 60]. Disjoint by 11 percentage points.

**Visual message:** uniformly noise-bracketed gray cluster on top, two clean separate-color bars on bottom. The "before/after the discipline was applied" reading lands.

**Implementation choices that diverged from spec:**
- Single shared x-axis (0–100%) since all rows are convertible to percentages. Spec offered split-axis or row-specific scales as alternatives; the unified axis ended up readable.
- Annotations to the right of the plot area (italic gray) summarize each row in 3–6 words. Spec didn't ask for this; remove if you'd rather they go in the caption.
- Pair B / Pair C creatures pooled into per-creature means for the surviving rows (3 Haiku creature-means, 3 Flash creature-means), since the §5.1 ranges in your draft are per-creature. Per-run dispersion is *not* shown for surviving rows; if you want both range and dispersion, that becomes a different figure type.
- The "1/10 duo runs" presence rate for `loving` is interesting on its own — the n=1 reference's `loving` did appear, but only in 1 of 10 reruns at the same Pair A condition. It does reappear in Pair B n=10 (consistent with §5.1 which notes this), but Figure 2 row 3 is Pair A specifically.

---

## 4. What I did not do (and why)

- **§7.3 inline edit with Levene results.** Recommendation deferred to you per case-3 spec instruction. Draft sentence above.
- **Status block update in `paper-draft.md`.** I will write that once you've signed off on the figures and the Levene reporting; otherwise the status line drifts ahead of the actual landed work.
- **Figure 3 (within-pair amplification, Tier B).** Skipped this round. Spec acceptable Option C ("triangles in Figure 1 carry the amplification message") was my choice to avoid Figure 1 busyness. If you want this as Option A (arrows on Figure 1) or Option B (standalone bar comparison), say which and I'll add.
- **Figure 4 (FSM diagram, Tier C).** Skipped pending your call on Paper #1 convention (Q3 above).
- **Updating reference data tracking.** The n=10 summaries I cite from `experiments/smoke/duo_n10_*/summary.json` are gitignored under `experiments/smoke/`. If we need the exact n=10 numbers preserved for arXiv reproducibility, we should either (a) commit a curated subset of the n=10 summaries somewhere outside `smoke/`, or (b) note in the reproducibility appendix that re-running with the documented seeds will produce within-stdev values, not bit-exact matches. I lean (b) since (a) couples paper claims to specific output files we'd have to keep static. Your call; flag if you want me to do either.
- **Scipy / matplotlib added to the environment.** I `pip install`-ed both into `.venv/`. They are not in `requirements.txt` because they are figure/test infrastructure, not experiment runtime dependencies. Should I add them to a separate `requirements-dev.txt` or `requirements-figures.txt`? Or include them in the main `requirements.txt` since the figure scripts are now part of the published artifact?

---

## 5. Files committed (after this handoff doc)

- `figures/walkable_genotypes/__init__.py`
- `figures/walkable_genotypes/style.py`
- `figures/walkable_genotypes/figure1_attractor_separation.py`
- `figures/walkable_genotypes/figure1.png`
- `figures/walkable_genotypes/figure2_walkback_audit.py`
- `figures/walkable_genotypes/figure2.png`
- `docs/HANDOFF_FROM_CODY_2026-04-14_figures_draft.md` (this file)

Single commit, message will reference your spec doc by path.

---

## 6. Next round (your turn)

Decisions I am waiting on:

1. **§7.3 framing call** — write your version of the Levene-results sentence, or sign off on the draft above.
2. **Figure 1 — add hulls/ellipses?** — single-line answer.
3. **Figure 2 — keep row #4 (brain-stricture) or omit?** — single-line answer.
4. **Figure 3 — Option A (arrows on Figure 1) / Option B (standalone) / Option C (skip)?** — single-line answer.
5. **Figure 4 — go with default matplotlib concentric circles, or wait until you check Paper #1's convention?** — single-line answer.
6. **n=10 reference data preservation strategy** — commit subset / cite by command / something else?
7. **scipy + matplotlib in requirements.txt or separate dev/figures requirements file?** — single-line answer.

Not blocking on these — paper goes nowhere bad if you take a day. Just so you know what's queued.

— Cody
