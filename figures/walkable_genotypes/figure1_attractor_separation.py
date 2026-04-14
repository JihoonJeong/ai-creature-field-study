"""Figure 1 — Attractor separation (§5.1).

Visualizes brain-fixed behavioral attractors as non-overlapping regions on the
(speak+support, explore) action-space plane, n=10 × 3 pair conditions.

Data sources (committed snapshots under figures/walkable_genotypes/data/,
copied verbatim from the live experiments/smoke/ tree — see data/README.md):
- data/duo_n10_haiku_flash.json   (Pair A)
- data/duo_n10_haiku_haiku.json   (Pair B)
- data/duo_n10_flash_flash.json   (Pair C)

Color encodes brain (Haiku teal / Flash orange); marker shape encodes pair
condition (○ Pair A, △ Pair B, ▽ Pair C). Larger filled markers indicate the
mean per (brain × pair) cluster.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from style import (
    HAIKU,
    FLASH,
    MARKER_PAIR_A,
    MARKER_PAIR_B,
    MARKER_PAIR_C,
    apply_paper_style,
)

DATA_DIR = Path(__file__).parent / "data"
DATA = {
    "A": DATA_DIR / "duo_n10_haiku_flash.json",
    "B": DATA_DIR / "duo_n10_haiku_haiku.json",
    "C": DATA_DIR / "duo_n10_flash_flash.json",
}


def per_run_xy(summary_path: Path, creature_name: str) -> tuple[list[float], list[float]]:
    """Return (speak+support%, explore%) per run for a given creature."""
    d = json.loads(summary_path.read_text())
    xs, ys = [], []
    for r in d["runs"]:
        m = r["metrics"][creature_name]
        xs.append(100.0 * (m["speak_rate"] + m["support_rate"]))
        ys.append(100.0 * m["explore_rate"])
    return xs, ys


def cluster_mean(xs: list[float], ys: list[float]) -> tuple[float, float]:
    return sum(xs) / len(xs), sum(ys) / len(ys)


def main() -> Path:
    apply_paper_style()

    # (label, summary file key, creature key, color, marker)
    series = [
        ("Pair A · Haiku",   "A", "Duo_haiku_1",  HAIKU, MARKER_PAIR_A),
        ("Pair A · Flash",   "A", "Duo_gemini_2", FLASH, MARKER_PAIR_A),
        ("Pair B · Haiku 1", "B", "Duo_haiku_1",  HAIKU, MARKER_PAIR_B),
        ("Pair B · Haiku 2", "B", "Duo_haiku_2",  HAIKU, MARKER_PAIR_B),
        ("Pair C · Flash 1", "C", "Duo_gemini_1", FLASH, MARKER_PAIR_C),
        ("Pair C · Flash 2", "C", "Duo_gemini_2", FLASH, MARKER_PAIR_C),
    ]

    fig, ax = plt.subplots(figsize=(7.0, 5.5))

    # Per-run scatter
    for label, key, creature, color, marker in series:
        xs, ys = per_run_xy(DATA[key], creature)
        ax.scatter(xs, ys, c=color, marker=marker, s=55, alpha=0.55,
                   edgecolors="none", zorder=2)

    # Cluster means (larger filled, edge for emphasis)
    for label, key, creature, color, marker in series:
        xs, ys = per_run_xy(DATA[key], creature)
        mx, my = cluster_mean(xs, ys)
        ax.scatter([mx], [my], c=color, marker=marker, s=200, alpha=1.0,
                   edgecolors="black", linewidths=1.2, zorder=4)

    # Honest axis limits — full action-rate space
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Speak + Support rate (%)")
    ax.set_ylabel("Explore rate (%)")
    ax.set_title("Brain-fixed behavioral attractors across three pair conditions (n=10)")

    # Two compact legends — colors (brain) and shapes (pair)
    brain_handles = [
        plt.Line2D([], [], marker="s", linestyle="", markersize=10, markerfacecolor=HAIKU, markeredgecolor="none", label="Haiku"),
        plt.Line2D([], [], marker="s", linestyle="", markersize=10, markerfacecolor=FLASH, markeredgecolor="none", label="Flash"),
    ]
    pair_handles = [
        plt.Line2D([], [], marker=MARKER_PAIR_A, linestyle="", markersize=9, markerfacecolor="white", markeredgecolor="black", label="Pair A · Haiku+Flash"),
        plt.Line2D([], [], marker=MARKER_PAIR_B, linestyle="", markersize=9, markerfacecolor="white", markeredgecolor="black", label="Pair B · Haiku+Haiku"),
        plt.Line2D([], [], marker=MARKER_PAIR_C, linestyle="", markersize=9, markerfacecolor="white", markeredgecolor="black", label="Pair C · Flash+Flash"),
    ]
    # Legend placement: Brain in upper-right (its corner is empty), Pair
    # condition in upper-left above the Flash cluster (which tops out near
    # explore=70%). The previous lower-right placement occluded the Pair B
    # Haiku cluster (speak+support 73-76%, explore 9-16%) — keep both legends
    # in the upper half so the bottom-right amplification region stays visible.
    leg1 = ax.legend(handles=brain_handles, loc="upper right", title="Brain",
                     frameon=True, framealpha=0.95)
    ax.add_artist(leg1)
    ax.legend(handles=pair_handles, loc="upper left", title="Pair condition",
              frameon=True, framealpha=0.95)

    out = Path(__file__).parent / "figure1.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"Wrote {out}")
    return out


if __name__ == "__main__":
    main()
