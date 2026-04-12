"""
Experiment: Does lived experience change behavior?

Group A (experienced): Wilderness #1 → reflection → Wilderness #2
Group B (fresh): skip → skip → Wilderness #2

Both face identical events in Wilderness #2 (same seed).
Difference: Group A has memories + SELF.md from Wilderness #1.

Run:
    python experiments/experience_effect_experiment.py
    python experiments/experience_effect_experiment.py --brain gemini_cli:gemini-2.5-flash
    python experiments/experience_effect_experiment.py --seeds 42,99,7
"""

from __future__ import annotations

import os
import sys
import json
import time
import shutil
import argparse
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
# Pin cwd to this repo so relative output paths (experiments/*_results/) never
# leak into a parent/sibling Ludex checkout when the script is launched from a
# drifted shell cwd.
os.chdir(_REPO_ROOT)

from ludex.core.organism_config import OrganismConfig
from ludex.core.habitat import HabitatConfig
from ludex.core.selfhood import reflect
from ludex.fields.wilderness import Wilderness
from ludex.viewers.session_report import generate_report


def make_creature(name: str, provider: str, model: str, habitat_dir: str):
    """Create a fresh creature."""
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


def run_wilderness(config, seed, ticks, run_dir, name):
    """Build organism and run wilderness. Returns log path."""
    org = config.build()
    wild = Wilderness(
        total_ticks=ticks,
        output_dir=run_dir,
        name=name,
        seed=seed,
        auto_reflect=False,
        auto_dream=False,
    )
    wild.join(org)
    wild.run()
    logs = list(Path(run_dir).glob("wilderness_*.json"))
    return str(logs[0]) if logs else "", org


def analyze(log_path: str, creature_name: str) -> dict:
    """Extract metrics from log."""
    with open(log_path) as f:
        data = json.load(f)

    ticks = data.get("ticks", [])
    creatures = data.get("creatures", [])

    for c in creatures:
        if c["name"] == creature_name:
            actions = c.get("actions", [])
            action_counts = {}
            for a in actions:
                action_counts[a] = action_counts.get(a, 0) + 1

            emotions = []
            for tick in ticks:
                for cd in tick.get("creatures", []):
                    if cd.get("name") == creature_name:
                        e = cd.get("emotion", "")
                        if e:
                            emotions.append(e)

            return {
                "action_counts": action_counts,
                "action_diversity": len(action_counts),
                "emotion_diversity": len(set(emotions)),
                "unique_emotions": sorted(set(emotions)),
                "cooperation_rate": round((action_counts.get("support", 0) + action_counts.get("trade", 0)) / max(len(actions), 1), 2),
                "defend_rate": round(action_counts.get("defend", 0) / max(len(actions), 1), 2),
                "explore_rate": round(action_counts.get("explore", 0) / max(len(actions), 1), 2),
                "final_energy": c.get("final_energy", 0),
                "emotions_sequence": emotions,
            }
    return {}


def run_single(provider, model, seed_train, seed_test, ticks, output_base, run_id):
    """Run one pair: experienced vs fresh, on seed_test."""
    print(f"\n{'='*60}")
    print(f"  Run {run_id}: train_seed={seed_train}, test_seed={seed_test}")
    print(f"{'='*60}")

    # === Group A: Experienced ===
    print(f"\n  [A] Experienced creature — training phase")
    config_a = make_creature(
        f"Exp_A_{run_id}", provider, model,
        f"{output_base}/creatures/exp_a_{run_id}",
    )

    # Training: Wilderness #1
    train_dir = f"{output_base}/train_a_{run_id}"
    log_train, org_a = run_wilderness(config_a, seed_train, ticks, train_dir, f"train_{run_id}")

    # Reflection
    engine_a = org_a.get_block("engine")
    print(f"  [A] Reflecting on training experience...")
    reflect(org_a, trigger="wilderness_training", engine=engine_a)

    # Read SELF.md
    self_md = Path(config_a.habitat.home_dir) / "SELF.md"
    self_content = self_md.read_text(encoding="utf-8") if self_md.exists() else ""
    self_preview = [l.strip() for l in self_content.split("\n") if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("*") and not l.strip().startswith("Last")][:2]
    print(f"  [A] SELF.md: {' | '.join(self_preview)[:150]}")

    # Test: Wilderness #2 (reload to pick up SELF.md)
    print(f"\n  [A] Testing phase (seed={seed_test})")
    config_a_reload = OrganismConfig.load(config_a.habitat.home_dir)
    test_dir_a = f"{output_base}/test_a_{run_id}"
    log_test_a, _ = run_wilderness(config_a_reload, seed_test, ticks, test_dir_a, f"test_a_{run_id}")

    # === Group B: Fresh ===
    print(f"\n  [B] Fresh creature — no training, straight to test")
    config_b = make_creature(
        f"Exp_B_{run_id}", provider, model,
        f"{output_base}/creatures/exp_b_{run_id}",
    )
    test_dir_b = f"{output_base}/test_b_{run_id}"
    log_test_b, _ = run_wilderness(config_b, seed_test, ticks, test_dir_b, f"test_b_{run_id}")

    # Analyze test runs
    metrics_a = analyze(log_test_a, f"Exp_A_{run_id}")
    metrics_b = analyze(log_test_b, f"Exp_B_{run_id}")

    # Generate reports
    generate_report(log_test_a, output=f"{output_base}/report_a_{run_id}.md")
    generate_report(log_test_b, output=f"{output_base}/report_b_{run_id}.md")

    return metrics_a, metrics_b


def main():
    parser = argparse.ArgumentParser(description="Experience Effect Experiment")
    parser.add_argument("--brain", default="claude_cli:haiku", help="provider:model")
    parser.add_argument("--ticks", type=int, default=10)
    parser.add_argument("--seeds", default="42,99,7", help="comma-separated seeds for training")
    parser.add_argument("--test-seed", type=int, default=123, help="fixed seed for all test runs")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. Default: experiments/experience_results/<provider>_<model>. "
             "Specify a separate dir (e.g. experiments/smoke/...) to avoid overwriting committed reference data.",
    )
    args = parser.parse_args()

    provider, model = args.brain.split(":", 1)
    seeds = [int(s) for s in args.seeds.split(",")]
    output_base = args.output_dir or f"experiments/experience_results/{provider}_{model.replace('.', '_')}"
    Path(output_base).mkdir(parents=True, exist_ok=True)

    all_a = []
    all_b = []

    for i, seed_train in enumerate(seeds):
        ma, mb = run_single(provider, model, seed_train, args.test_seed, args.ticks, output_base, f"r{i+1}")
        all_a.append(ma)
        all_b.append(mb)

    # === Summary ===
    print(f"\n\n{'='*70}")
    print(f"  EXPERIENCE EFFECT — {provider}:{model}")
    print(f"  {len(seeds)} runs, train_seeds={seeds}, test_seed={args.test_seed}, ticks={args.ticks}")
    print(f"{'='*70}")

    def avg(lst, key):
        vals = [m.get(key, 0) for m in lst]
        return sum(vals) / len(vals) if vals else 0

    metrics = ["action_diversity", "emotion_diversity", "defend_rate", "explore_rate", "final_energy", "cooperation_rate"]

    print(f"\n  {'Metric':<22} {'Experienced':>12} {'Fresh':>12} {'Delta':>12}")
    print(f"  {'-'*58}")
    for metric in metrics:
        va = avg(all_a, metric)
        vb = avg(all_b, metric)
        delta = va - vb
        if "rate" in metric:
            print(f"  {metric:<22} {va:>11.0%} {vb:>11.0%} {delta:>+11.0%}")
        else:
            print(f"  {metric:<22} {va:>12.1f} {vb:>12.1f} {delta:>+12.1f}")

    # Per-run detail
    print(f"\n  Per-run emotions:")
    for i in range(len(seeds)):
        ea = all_a[i].get("unique_emotions", [])
        eb = all_b[i].get("unique_emotions", [])
        print(f"    Run {i+1}: A={ea}  B={eb}")

    # Save
    summary = {
        "brain": f"{provider}:{model}",
        "seeds_train": seeds,
        "seed_test": args.test_seed,
        "ticks": args.ticks,
        "experienced": all_a,
        "fresh": all_b,
    }
    with open(f"{output_base}/summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Summary: {output_base}/summary.json")


if __name__ == "__main__":
    main()
