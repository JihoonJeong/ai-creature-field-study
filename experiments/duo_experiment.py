"""
Experiment: Two experienced creatures with different brains meet.

Both creatures:
1. Train in Wilderness #1 (solo, different seed per creature)
2. Reflect → SELF.md
3. Meet in shared Wilderness #2 (same seed, together)

Questions:
- Do creatures with opposite adaptation strategies cooperate or clash?
- Does the presence of another creature change individual behavior?
- Do bonds form differently based on brain pairing?

Run:
    python experiments/duo_experiment.py
    python experiments/duo_experiment.py --brains claude_cli:haiku,gemini_cli:gemini-2.5-flash
"""

from __future__ import annotations

import os
import sys
import json
import time
import shutil
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
# Pin cwd to this repo so relative output paths never leak into a parent/sibling
# Ludex checkout when the script is launched from a drifted shell cwd.
os.chdir(_REPO_ROOT)

from ludex.core.organism_config import OrganismConfig
from ludex.core.habitat import HabitatConfig
from ludex.core.selfhood import reflect, load_self
from ludex.fields.wilderness import Wilderness
from ludex.viewers.session_report import generate_report


def make_creature(name, provider, model, habitat_dir):
    if os.path.exists(habitat_dir):
        shutil.rmtree(habitat_dir)
    habitat = HabitatConfig.local(habitat_dir, max_mb=100)
    config = OrganismConfig(
        name=name,
        brain={"provider": provider, "model": model},
        habitat=habitat,
    )
    config.organs["memory"]["enabled"] = True
    config.organs["emotion"]["enabled"] = True
    config.organs["immune"]["enabled"] = True
    enabled = config.get_enabled_organs()
    config.organs["engine"]["system_prompt"] = (
        f"You are {name}, a Ludex creature. "
        f"Brain: {model}. Organs: {', '.join(enabled)}. "
        f"You are curious and authentic. Be brief (2-3 sentences)."
    )
    config.save()
    config.habitat.write_identity_files(
        creature_name=name, brain_model=model,
        brain_provider=provider, organs=enabled,
    )
    return config


def train_creature(config, seed, ticks, run_dir):
    """Solo training wilderness + reflection."""
    org = config.build()
    wild = Wilderness(
        total_ticks=ticks, output_dir=run_dir, name=f"train_{config.name}",
        seed=seed, auto_reflect=False, auto_dream=False,
    )
    wild.join(org)
    wild.run()
    # Reflect
    engine = org.get_block("engine")
    reflect(org, trigger="training_complete", engine=engine)
    return org


def analyze_duo(log_path, creature_names):
    with open(log_path) as f:
        data = json.load(f)
    results = {}
    for c in data.get("creatures", []):
        name = c["name"]
        actions = c.get("actions", [])
        counts = {}
        for a in actions:
            counts[a] = counts.get(a, 0) + 1
        emotions = []
        for tick in data.get("ticks", []):
            for cd in tick.get("creatures", []):
                if cd.get("name") == name:
                    e = cd.get("emotion", "")
                    if e:
                        emotions.append(e)
        results[name] = {
            "action_counts": counts,
            "action_diversity": len(counts),
            "emotion_diversity": len(set(emotions)),
            "unique_emotions": sorted(set(emotions)),
            "speak_rate": round(counts.get("speak", 0) / max(len(actions), 1), 2),
            "support_rate": round(counts.get("support", 0) / max(len(actions), 1), 2),
            "defend_rate": round(counts.get("defend", 0) / max(len(actions), 1), 2),
            "explore_rate": round(counts.get("explore", 0) / max(len(actions), 1), 2),
            "final_energy": c.get("final_energy", 0),
        }
    return results


def run_single(brain_specs, train_seed, test_seed, ticks, output_base, run_id):
    """One full duo run: create creatures → train each → duo wilderness → analyze."""
    run_dir = output_base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    creatures = []
    for i, spec in enumerate(brain_specs):
        provider, model = spec.split(":", 1)
        name = f"Duo_{model.split('-')[0]}_{i+1}"
        habitat_dir = str(run_dir / f"creatures/{name.lower()}")
        config = make_creature(name, provider, model, habitat_dir)
        creatures.append({"name": name, "config": config, "provider": provider, "model": model})

    print(f"\n{'='*60}\n  {run_id}: PHASE 1 Solo Training (train_seed={train_seed})\n{'='*60}")
    for c in creatures:
        print(f"\n  Training {c['name']} ({c['model']})...")
        train_dir = str(run_dir / f"train_{c['name'].lower()}")
        train_creature(c["config"], train_seed, ticks, train_dir)
        self_content = load_self(c["config"].habitat.home_dir)
        lines = [l.strip() for l in self_content.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("*") and not l.startswith("Last")]
        print(f"  SELF.md: {lines[0][:120] if lines else '(empty)'}")

    print(f"\n{'='*60}\n  {run_id}: PHASE 2 Duo Wilderness (test_seed={test_seed})\n{'='*60}")
    orgs = []
    for c in creatures:
        config_reload = OrganismConfig.load(c["config"].habitat.home_dir)
        orgs.append(config_reload.build())

    test_dir = str(run_dir / "duo_test")
    wild = Wilderness(
        total_ticks=ticks, output_dir=test_dir, name="duo_test",
        seed=test_seed, auto_reflect=True, auto_dream=True,
    )
    for org in orgs:
        wild.join(org)
    wild.run()

    metrics = {}
    logs = list(Path(test_dir).glob("wilderness_*.json"))
    if logs:
        log_path = str(logs[0])
        generate_report(log_path, output=str(run_dir / "duo_report.md"))
        metrics = analyze_duo(log_path, [c["name"] for c in creatures])
        for name, m in metrics.items():
            brain = next((c["model"] for c in creatures if c["name"] == name), "?")
            print(f"  {name} ({brain}): speak={m['speak_rate']:.0%} defend={m['defend_rate']:.0%} "
                  f"explore={m['explore_rate']:.0%} emotions={m['unique_emotions']} energy={m['final_energy']}")

    return {
        "run_id": run_id,
        "train_seed": train_seed,
        "test_seed": test_seed,
        "brains": [c["model"] for c in creatures],
        "metrics": metrics,
    }


def aggregate(runs, creature_names):
    """Mean ± variance for key rates across runs, per creature position."""
    import statistics
    keys = ["speak_rate", "support_rate", "defend_rate", "explore_rate", "final_energy"]
    agg = {}
    for name in creature_names:
        rows = [r["metrics"][name] for r in runs if name in r["metrics"]]
        if not rows:
            continue
        agg[name] = {}
        for k in keys:
            vals = [row[k] for row in rows]
            agg[name][k] = {
                "mean": round(statistics.mean(vals), 3),
                "stdev": round(statistics.stdev(vals), 3) if len(vals) > 1 else 0.0,
                "n": len(vals),
            }
        agg[name]["emotion_union"] = sorted({e for row in rows for e in row["unique_emotions"]})
    return agg


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--brains", default="claude_cli:haiku,gemini_cli:gemini-2.5-flash")
    parser.add_argument("--ticks", type=int, default=10)
    parser.add_argument(
        "--train-seeds", default=None,
        help="Comma-separated train seeds — one duo run per seed. If omitted, falls back to --train-seed.",
    )
    parser.add_argument("--train-seed", type=int, default=42, help="Single train seed (used if --train-seeds not given).")
    parser.add_argument("--test-seed", type=int, default=123)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. Default: experiments/duo_results. "
             "Specify a separate dir (e.g. experiments/smoke/...) to avoid overwriting committed reference data.",
    )
    args = parser.parse_args()

    brain_specs = [b.strip() for b in args.brains.split(",")]
    output_base = Path(args.output_dir) if args.output_dir else Path("experiments/duo_results")
    output_base.mkdir(parents=True, exist_ok=True)

    if args.train_seeds:
        train_seeds = [int(s) for s in args.train_seeds.split(",")]
    else:
        train_seeds = [args.train_seed]

    runs = []
    for i, ts in enumerate(train_seeds):
        run = run_single(brain_specs, ts, args.test_seed, args.ticks, output_base, f"r{i+1}")
        runs.append(run)

    creature_names = sorted({name for r in runs for name in r["metrics"]})
    agg = aggregate(runs, creature_names) if len(runs) > 1 else {}

    from model_versions import record_brain_versions
    summary = {
        "brains": brain_specs,
        "brain_versions": record_brain_versions(brain_specs),
        "train_seeds": train_seeds,
        "test_seed": args.test_seed,
        "ticks": args.ticks,
        "n_runs": len(runs),
        "runs": runs,
        "aggregate": agg,
    }
    with open(output_base / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Summary: {output_base}/summary.json")
    if agg:
        print(f"\n{'='*60}\n  AGGREGATE across {len(runs)} runs\n{'='*60}")
        for name, stats in agg.items():
            print(f"\n  {name}:")
            for k in ["speak_rate", "support_rate", "defend_rate", "explore_rate", "final_energy"]:
                s = stats[k]
                print(f"    {k}: mean={s['mean']} stdev={s['stdev']} (n={s['n']})")
            print(f"    emotion_union: {stats['emotion_union']}")


if __name__ == "__main__":
    main()
