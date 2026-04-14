"""Figure 2 — Walk-back audit (§4.4 / §7.1).

Forest-style plot showing, top-to-bottom: four walked-back claims (gray)
followed by the surviving brain-fixed attractor claim (teal/orange) on two
metrics. A horizontal separator splits the noise-dominated walk-backs from
the unambiguous surviving claim.

Each row uses a percentage (0-100) scale for visual unity. The visual
message: walk-back rows show overlapping or noise-bracketed estimates;
surviving rows show non-overlapping per-brain ranges.

Data sources (committed snapshots under data/, see data/README.md):
- data/experience_pilot_n5.json     (#1)
- data/duo_n10_haiku_flash.json     (#2, #3 emotion check, surviving claim)
- data/duo_n10_haiku_haiku.json     (surviving claim)
- data/duo_n10_flash_flash.json     (surviving claim)
- data/brain_stricture.json         (#4, copied from Ludex track)
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from style import HAIKU, FLASH, NEUTRAL, apply_paper_style

DATA_DIR = Path(__file__).parent / "data"
EXPERIENCE_PILOT  = DATA_DIR / "experience_pilot_n5.json"
DUO_N10_PAIR_A    = DATA_DIR / "duo_n10_haiku_flash.json"
DUO_N10_PAIR_B    = DATA_DIR / "duo_n10_haiku_haiku.json"
DUO_N10_PAIR_C    = DATA_DIR / "duo_n10_flash_flash.json"
LUDEX_STRICTURE   = DATA_DIR / "brain_stricture.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def collect_walkback_rows() -> list[dict]:
    """Build the four walked-back rows. Each row has:
    label, points (list of (x, low, high, color, marker)), units, note.
    """
    rows: list[dict] = []

    # #1 Experience → caution: defend_rate A vs B (n=5 pilot)
    exp = load(EXPERIENCE_PILOT)
    a_def = [r["defend_rate"] for r in exp["experienced"]]
    b_def = [r["defend_rate"] for r in exp["fresh"]]
    rows.append({
        "label": "1. Experience → caution\n(defend rate, n=5)",
        "points": [
            ("A: experienced", 100*statistics.mean(a_def), 100*statistics.stdev(a_def)),
            ("B: fresh",       100*statistics.mean(b_def), 100*statistics.stdev(b_def)),
        ],
        "annot": "directions overlap inside ±1σ",
    })

    # #2 Social presence → no defense: Pair A duo defend, Haiku vs Flash (n=10)
    pa = load(DUO_N10_PAIR_A)
    h_def = [r["metrics"]["Duo_haiku_1"]["defend_rate"]  for r in pa["runs"]]
    f_def = [r["metrics"]["Duo_gemini_2"]["defend_rate"] for r in pa["runs"]]
    rows.append({
        "label": "2. Social → no defense\n(duo defend, n=10)",
        "points": [
            ("Haiku duo", 100*statistics.mean(h_def), 100*statistics.stdev(h_def)),
            ("Flash duo", 100*statistics.mean(f_def), 100*statistics.stdev(f_def)),
        ],
        "annot": "claim 'duo ≈ 3%' fits Haiku, not Flash",
    })

    # #3 Emotion flip → loving: presence rate of 'loving' in n=10 duo runs (Pair A)
    loving_present = sum(1 for r in pa["runs"]
                         if "loving" in r["metrics"]["Duo_haiku_1"].get("unique_emotions", [])
                         or "loving" in r["metrics"]["Duo_gemini_2"].get("unique_emotions", []))
    n_runs = len(pa["runs"])
    presence_pct = 100.0 * loving_present / n_runs
    rows.append({
        "label": "3. Emotion flip → 'loving'\n(presence rate, Pair A n=10)",
        "points": [
            ("any creature", presence_pct, 0.0),
        ],
        "annot": f"appeared in {loving_present}/{n_runs} duo runs",
    })

    # #4 Brain-stricture (Ludex ToM track): ✓ rates with binomial-style 1/n bound
    if LUDEX_STRICTURE.exists():
        s = load(LUDEX_STRICTURE)
        n = s["n"]
        h_ok = s["haiku_on_flash"].get("\u2713", 0)
        f_ok = s["flash_on_haiku"].get("\u2713", 0)
        # rough ±1σ on a binomial proportion at n=10: sqrt(p(1-p)/n)
        def pse(k, n):
            p = k/n
            return p, 100.0 * (p*(1-p)/n)**0.5
        h_p, h_sd = pse(h_ok, n)
        f_p, f_sd = pse(f_ok, n)
        rows.append({
            "label": "4. Brain-stricture\n(✓ rate, n=10, Ludex track)",
            "points": [
                (f"Haiku ✓ {h_ok}/{n}", 100*h_p, h_sd),
                (f"Flash ✓ {f_ok}/{n}", 100*f_p, f_sd),
            ],
            "annot": "predicted asymmetry collapsed",
        })
    else:
        rows.append({
            "label": "4. Brain-stricture\n(Ludex track, not in this repo)",
            "points": [],
            "annot": "external track — see §4.4",
        })
    return rows


def collect_surviving_rows() -> list[dict]:
    """Two surviving-claim rows: per-brain mean ranges across the n=10 pairs."""
    pa = load(DUO_N10_PAIR_A)
    pb = load(DUO_N10_PAIR_B)
    pc = load(DUO_N10_PAIR_C)

    def pct_range(creature_specs):
        """creature_specs: list of (summary_dict, creature_name) -> per-creature mean."""
        means = []
        for d, name in creature_specs:
            for k in ("speak_rate","support_rate","explore_rate"):
                pass
        return means

    def per_creature_mean(d, name, key):
        return statistics.mean(r["metrics"][name][key] for r in d["runs"])

    def speak_support_mean(d, name):
        return per_creature_mean(d, name, "speak_rate") + per_creature_mean(d, name, "support_rate")

    haiku_creatures = [
        (pa, "Duo_haiku_1"), (pb, "Duo_haiku_1"), (pb, "Duo_haiku_2"),
    ]
    flash_creatures = [
        (pa, "Duo_gemini_2"), (pc, "Duo_gemini_1"), (pc, "Duo_gemini_2"),
    ]

    rows = []

    # Speak+support
    h_means = [100*speak_support_mean(d, n) for d, n in haiku_creatures]
    f_means = [100*speak_support_mean(d, n) for d, n in flash_creatures]
    rows.append({
        "label": "5. Attractor: speak+support\n(per-creature means, n=10)",
        "ranges": [
            ("Haiku", min(h_means), max(h_means), HAIKU),
            ("Flash", min(f_means), max(f_means), FLASH),
        ],
        "annot": "non-overlapping per-brain ranges",
    })

    # Explore
    h_means = [100*per_creature_mean(d, n, "explore_rate") for d, n in haiku_creatures]
    f_means = [100*per_creature_mean(d, n, "explore_rate") for d, n in flash_creatures]
    rows.append({
        "label": "6. Attractor: explore\n(per-creature means, n=10)",
        "ranges": [
            ("Haiku", min(h_means), max(h_means), HAIKU),
            ("Flash", min(f_means), max(f_means), FLASH),
        ],
        "annot": "non-overlapping per-brain ranges",
    })

    return rows


def main() -> Path:
    apply_paper_style()
    walk_rows = collect_walkback_rows()
    surv_rows = collect_surviving_rows()
    rows = walk_rows + surv_rows
    n = len(rows)

    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    y_positions = list(range(n, 0, -1))  # top-down

    # Walk-back rows: gray points with ±1σ horizontal whiskers
    for y, row in zip(y_positions[:len(walk_rows)], walk_rows):
        for i, (lbl, mean, sd) in enumerate(row["points"]):
            offset = 0.18 if len(row["points"]) > 1 and i == 0 else (-0.18 if len(row["points"]) > 1 else 0)
            ax.errorbar(mean, y + offset, xerr=sd, fmt="o", color=NEUTRAL,
                        ecolor=NEUTRAL, elinewidth=1.5, capsize=4, markersize=8, alpha=0.95)
            ax.text(mean + sd + 1.5, y + offset, lbl, fontsize=8,
                    color="#555555", verticalalignment="center")
        ax.text(101, y, row["annot"], fontsize=8, style="italic",
                color="#555555", verticalalignment="center")

    # Separator
    sep_y = len(surv_rows) + 0.5
    ax.axhline(sep_y, color="#666666", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.text(50, sep_y + 0.15, "— walked back —", fontsize=8, style="italic",
            color="#777777", horizontalalignment="center", verticalalignment="bottom")
    ax.text(50, sep_y - 0.15, "— survived —", fontsize=8, style="italic",
            color="#444444", horizontalalignment="center", verticalalignment="top",
            fontweight="bold")

    # Surviving rows: two color bars per row (Haiku + Flash ranges)
    for y, row in zip(y_positions[len(walk_rows):], surv_rows):
        for i, (lbl, lo, hi, color) in enumerate(row["ranges"]):
            offset = 0.18 if i == 0 else -0.18
            ax.plot([lo, hi], [y + offset, y + offset], color=color,
                    linewidth=5.0, alpha=0.9, solid_capstyle="round",
                    marker="|", markersize=12, markeredgewidth=2)
            ax.text(hi + 1.5, y + offset, f"{lbl}: [{lo:.0f}, {hi:.0f}]",
                    fontsize=8, color=color, verticalalignment="center", fontweight="bold")
        ax.text(101, y, row["annot"], fontsize=8, style="italic",
                color="#444444", verticalalignment="center")

    ax.set_xlim(-2, 145)
    ax.set_ylim(0.4, n + 0.6)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_yticks(y_positions)
    ax.set_yticklabels([r["label"] for r in rows])
    ax.set_xlabel("Rate (row-specific units; see annotations)")
    ax.set_title("Walk-back audit: four retracted headlines (gray) and one surviving claim (color)")

    # Hide vertical grid for clarity in this layout
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)

    out = Path(__file__).parent / "figure2.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"Wrote {out}")
    return out


if __name__ == "__main__":
    main()
