# Figure data — committed snapshot

The Walkable Genotypes paper figures load aggregate metrics from this directory
rather than the live `experiments/` tree, so the figures are bit-reproducible
from a fresh clone without re-running the experiment matrix.

| File | Source |
|---|---|
| `duo_n10_haiku_flash.json` | `experiments/smoke/duo_n10_haiku_flash/summary.json` (Pair A, n=10) |
| `duo_n10_haiku_haiku.json` | `experiments/smoke/duo_n10_haiku_haiku/summary.json` (Pair B, n=10) |
| `duo_n10_flash_flash.json` | `experiments/smoke/duo_n10_flash_flash/summary.json` (Pair C, n=10) |
| `experience_pilot_n5.json` | `experiments/smoke/experience_pilot_n5/summary.json` (walk-back #1) |
| `brain_stricture.json` | Ludex track, copied verbatim from a private parent repo for walk-back #4 (verdict counts only — no Ludex internals embedded) |

`experiments/smoke/` itself is gitignored. Re-running the experiment scripts
with the documented seeds will produce within-stdev values, not bit-exact
matches against these snapshots; that is the reproducibility level the paper
claims (§7.4, §9). The figures themselves should reproduce exactly from these
JSONs across machines and time.
