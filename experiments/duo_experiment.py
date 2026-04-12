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


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--brains", default="claude_cli:haiku,gemini_cli:gemini-2.5-flash")
    parser.add_argument("--ticks", type=int, default=10)
    parser.add_argument("--train-seed", type=int, default=42)
    parser.add_argument("--test-seed", type=int, default=123)
    args = parser.parse_args()

    brain_specs = [b.strip() for b in args.brains.split(",")]
    output_base = Path("experiments/duo_results")
    output_base.mkdir(parents=True, exist_ok=True)

    creatures = []
    for i, spec in enumerate(brain_specs):
        provider, model = spec.split(":", 1)
        name = f"Duo_{model.split('-')[0]}_{i+1}"
        habitat_dir = str(output_base / f"creatures/{name.lower()}")
        config = make_creature(name, provider, model, habitat_dir)
        creatures.append({"name": name, "config": config, "provider": provider, "model": model})

    # Phase 1: Solo training
    print(f"\n{'='*60}")
    print(f"  PHASE 1: Solo Training")
    print(f"{'='*60}")
    for c in creatures:
        print(f"\n  Training {c['name']} ({c['model']})...")
        train_dir = str(output_base / f"train_{c['name'].lower()}")
        train_creature(c["config"], args.train_seed, args.ticks, train_dir)
        self_content = load_self(c["config"].habitat.home_dir)
        lines = [l.strip() for l in self_content.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("*") and not l.startswith("Last")]
        print(f"  SELF.md: {lines[0][:120] if lines else '(empty)'}")

    # Phase 2: Duo wilderness
    print(f"\n{'='*60}")
    print(f"  PHASE 2: Duo Wilderness (seed={args.test_seed})")
    print(f"{'='*60}")

    orgs = []
    for c in creatures:
        config_reload = OrganismConfig.load(c["config"].habitat.home_dir)
        org = config_reload.build()
        orgs.append(org)

    test_dir = str(output_base / "duo_test")
    wild = Wilderness(
        total_ticks=args.ticks,
        output_dir=test_dir,
        name="duo_test",
        seed=args.test_seed,
        auto_reflect=True,
        auto_dream=True,
    )
    for org in orgs:
        wild.join(org)
    wild.run()

    # Analyze
    logs = list(Path(test_dir).glob("wilderness_*.json"))
    if logs:
        log_path = str(logs[0])
        report = generate_report(log_path, output=str(output_base / "duo_report.md"))

        metrics = analyze_duo(log_path, [c["name"] for c in creatures])

        print(f"\n{'='*60}")
        print(f"  DUO RESULTS")
        print(f"{'='*60}")
        for name, m in metrics.items():
            brain = next((c["model"] for c in creatures if c["name"] == name), "?")
            print(f"\n  {name} ({brain}):")
            print(f"    Actions: {m['action_counts']}")
            print(f"    Emotions: {m['unique_emotions']}")
            print(f"    Speak: {m['speak_rate']:.0%} | Support: {m['support_rate']:.0%} | "
                  f"Defend: {m['defend_rate']:.0%} | Explore: {m['explore_rate']:.0%}")
            print(f"    Energy: {m['final_energy']}")

    # Check bonds
    print(f"\n  === BONDS ===")
    for c in creatures:
        bonds_dir = Path(c["config"].habitat.home_dir) / "bonds"
        if bonds_dir.exists():
            for bond_file in bonds_dir.glob("*.md"):
                content = bond_file.read_text(encoding="utf-8")[:200]
                print(f"  {c['name']} → {bond_file.stem}: {content[:150]}")

    # Save summary
    summary = {
        "brains": [c["model"] for c in creatures],
        "train_seed": args.train_seed,
        "test_seed": args.test_seed,
        "ticks": args.ticks,
        "metrics": metrics if logs else {},
    }
    with open(output_base / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
