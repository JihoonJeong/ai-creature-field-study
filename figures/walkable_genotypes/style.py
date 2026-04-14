"""Shared style constants for Walkable Genotypes paper figures.

Color palette mirrors the SPEC (HANDOFF_FROM_LUCA_2026-04-13_figures_spec.md §3):
- Haiku: teal / muted blue
- Flash: orange / muted red
- Walked-back / noise: neutral gray
- Surviving / confirmed accent: green
"""
from __future__ import annotations

import matplotlib as mpl

# Brand colors
HAIKU = "#2B8CBE"
FLASH = "#E6550D"
NEUTRAL = "#999999"
CONFIRMED = "#2CA02C"

# Pair-condition marker shapes (matplotlib marker codes)
MARKER_PAIR_A = "o"  # circle — mixed pair
MARKER_PAIR_B = "^"  # triangle up — same-brain Haiku pair
MARKER_PAIR_C = "v"  # triangle down — same-brain Flash pair


def apply_paper_style() -> None:
    """Set rcParams to match the paper's visual conventions."""
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.color": "#CCCCCC",
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
