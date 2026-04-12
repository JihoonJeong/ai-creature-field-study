"""
Creature Selfhood — SELF.md + Bonds + Reflection

D-021: SELF.md emerges from reflection, not configuration.
D-022: Bonds are structured relationship records that grow from experience.

Inspired by gyeol (inureyes/gyeol), adapted for Ludex multi-creature model.

Usage:
    from ludex.core.selfhood import reflect, update_bond, load_self, load_bonds

    # After a Wilderness or Agora session
    reflect(organism, trigger="wilderness_complete")

    # After meeting another creature
    update_bond(organism, other_name="Spark", shared_experience="...")
"""

from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# SELF.md — emergent self-understanding
# ============================================================

def load_self(habitat_dir: str) -> str:
    """Read the creature's current SELF.md. Returns content or empty string."""
    path = Path(habitat_dir) / "SELF.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def load_self_compressed(habitat_dir: str) -> str:
    """Load SELF.md compressed for SLM prompt injection.

    Extracts key lines (behavioral patterns, lessons) and compresses
    to a short block suitable for system prompt.
    """
    content = load_self(habitat_dir)
    if not content or "empty at birth" in content:
        return ""

    # Strip XML tags that some brains (Gemini) wrap around content
    import re
    content = re.sub(r'<[^>]+>', '', content)
    # Strip markdown bold markers
    content = content.replace("**", "")

    # Extract meaningful lines (skip headers, empty lines, meta)
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("*") and stripped.endswith("*"):
            continue  # skip italic-only lines (e.g., *settles into reflection*)
        if stripped.startswith("- "):
            lines.append(stripped[2:])
        elif stripped.startswith("Last reflection"):
            continue
        else:
            lines.append(stripped)

    if not lines:
        return ""

    # Compress to max ~200 chars
    compressed = "; ".join(lines)
    if len(compressed) > 200:
        compressed = compressed[:200] + "..."
    return f"[Self] {compressed}"


def reflect(organism, trigger: str = "manual", engine=None) -> str:
    """Trigger a reflection cycle for the creature.

    The creature examines its recent memories and produces a self-assessment.
    The result is written to SELF.md in the habitat.

    Args:
        organism: The Organism instance
        trigger: What caused this reflection (wilderness_complete, agora_complete, periodic, manual)
        engine: EngineBlock to use (auto-detected if None)

    Returns:
        The reflection text, or empty string on failure.
    """
    config = getattr(organism, "config", None)
    if not config:
        return ""
    habitat_dir = config.get("habitat_dir", "") if hasattr(config, "get") else ""
    if not habitat_dir:
        return ""

    if engine is None:
        engine = organism.get_block("engine")
    if engine is None:
        return ""

    memory = organism.get_block("memory")

    # Gather recent memories for reflection material
    recent_memories = []
    if memory:
        try:
            stats = memory.stats()
            # Recall wilderness and agora experiences
            for query in ["wilderness", "agora", "important", "learned"]:
                results = memory.handle_recall(query, limit=5)
                for r in results:
                    content = r.memory.content if hasattr(r, "memory") else str(r)
                    if content not in recent_memories:
                        recent_memories.append(content)
        except Exception as e:
            logger.debug(f"Reflection: memory recall failed: {e}")

    # Read current SELF.md
    current_self = load_self(habitat_dir)

    # Read bonds
    bonds_summary = _summarize_bonds(habitat_dir)

    # Build reflection prompt
    memory_text = "\n".join(f"- {m[:150]}" for m in recent_memories[:15])
    prompt = (
        f"[Reflection — triggered by: {trigger}]\n\n"
        f"Take a moment to reflect on your recent experiences. "
        f"This is not a task — it's self-examination.\n\n"
        f"Your recent memories:\n{memory_text}\n\n"
    )
    if bonds_summary:
        prompt += f"Your relationships:\n{bonds_summary}\n\n"
    if current_self and "empty at birth" not in current_self:
        prompt += f"Your previous self-understanding:\n{current_self}\n\n"

    prompt += (
        "Now reflect honestly:\n"
        "1. **Behavioral patterns**: What do you tend to do under stress? In calm? With others?\n"
        "2. **What you've learned**: What has experience taught you?\n"
        "3. **Open questions**: What don't you understand about yourself yet?\n\n"
        "Write in first person. Be honest, not aspirational. "
        "Only write what you've actually observed about yourself. "
        "Keep it concise (10-15 lines max). "
        "Write plain text — no XML tags, no code blocks, no wrappers."
    )

    # Get reflection from the creature's brain
    try:
        result = engine.handle_submit(prompt)
        reflection_text = result.response or ""
    except Exception as e:
        logger.error(f"Reflection failed: {e}")
        return ""

    if not reflection_text:
        return ""

    # Write to SELF.md
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    self_content = (
        f"# {organism.name} — Self-Understanding\n"
        f"Last reflection: {now} (trigger: {trigger})\n\n"
        f"{reflection_text}\n"
    )

    self_path = Path(habitat_dir) / "SELF.md"
    try:
        self_path.write_text(self_content, encoding="utf-8")
        logger.info(f"SELF.md updated for {organism.name} ({len(reflection_text)} chars)")
    except Exception as e:
        logger.error(f"Failed to write SELF.md: {e}")

    # Store reflection as semantic memory
    if memory:
        try:
            memory.handle_remember(
                f"Self-reflection ({trigger}): {reflection_text[:300]}",
                memory_type="semantic",
                tags=["reflection", "self", trigger],
                source=f"reflection/{trigger}",
            )
        except Exception:
            pass

    return reflection_text


# ============================================================
# Bonds — structured relationship memory
# ============================================================

def load_bonds(habitat_dir: str) -> dict[str, str]:
    """Load all bond files from habitat. Returns {name: content}."""
    bonds_dir = Path(habitat_dir) / "bonds"
    if not bonds_dir.is_dir():
        return {}

    bonds = {}
    for path in sorted(bonds_dir.glob("*.md")):
        name = path.stem
        bonds[name] = path.read_text(encoding="utf-8")
    return bonds


def load_bonds_compressed(habitat_dir: str) -> str:
    """Load bonds compressed for SLM prompt injection."""
    bonds = load_bonds(habitat_dir)
    if not bonds:
        return ""

    lines = ["[Known beings]"]
    for name, content in bonds.items():
        # Extract first non-header, non-empty line as summary
        summary = ""
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("First met"):
                summary = stripped[:80]
                break
        if summary:
            lines.append(f"- {name}: {summary}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


def update_bond(
    organism,
    other_name: str,
    shared_experience: str,
    other_brain: str = "",
    engine=None,
) -> str:
    """Update or create a bond record after a shared experience.

    The creature reflects on the relationship and updates the bond file.
    For SLMs or when engine is unavailable, writes a simple factual record.

    Returns the bond content.
    """
    config = getattr(organism, "config", None)
    if not config:
        return ""
    habitat_dir = config.get("habitat_dir", "") if hasattr(config, "get") else ""
    if not habitat_dir:
        return ""

    bonds_dir = Path(habitat_dir) / "bonds"
    bonds_dir.mkdir(parents=True, exist_ok=True)
    bond_path = bonds_dir / f"{other_name.lower()}.md"

    # Read existing bond
    existing = ""
    if bond_path.exists():
        existing = bond_path.read_text(encoding="utf-8")

    if engine is None:
        engine = organism.get_block("engine")

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d")

    if engine:
        # Ask the creature to reflect on the relationship
        prompt = (
            f"[Bond reflection — {other_name}]\n\n"
            f"You just shared an experience with {other_name}"
            f"{' (brain: ' + other_brain + ')' if other_brain else ''}.\n\n"
            f"What happened: {shared_experience[:300]}\n\n"
        )
        if existing:
            prompt += f"Your existing understanding of {other_name}:\n{existing}\n\n"
        else:
            prompt += f"This is your first time reflecting on {other_name}.\n\n"

        prompt += (
            f"Write a brief bond record for {other_name}. Include:\n"
            f"- Who they are (personality, traits you observed)\n"
            f"- Key shared experiences\n"
            f"- What you've learned from this relationship\n"
            f"Keep it honest and concise (5-10 lines). First person."
        )

        try:
            result = engine.handle_submit(prompt)
            bond_text = result.response or ""
        except Exception:
            bond_text = ""
    else:
        bond_text = ""

    # Fallback: simple factual record
    if not bond_text:
        if existing:
            bond_text = existing.rstrip() + f"\n\n## Update {now}\n{shared_experience[:200]}\n"
        else:
            bond_text = (
                f"# Bond: {other_name}\n"
                f"First met: {now}\n"
                f"Brain: {other_brain}\n\n"
                f"## Shared history\n- {shared_experience[:200]}\n"
            )
    else:
        # Wrap engine reflection in proper header
        if not bond_text.startswith("#"):
            bond_text = f"# Bond: {other_name}\nFirst met: {now}\nBrain: {other_brain}\n\n{bond_text}"

    try:
        bond_path.write_text(bond_text, encoding="utf-8")
        logger.info(f"Bond updated: {organism.name} → {other_name}")
    except Exception as e:
        logger.error(f"Failed to write bond {other_name}: {e}")

    return bond_text


def _summarize_bonds(habitat_dir: str) -> str:
    """Summarize all bonds for reflection context."""
    bonds = load_bonds(habitat_dir)
    if not bonds:
        return ""
    lines = []
    for name, content in bonds.items():
        # First meaningful line
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(f"- {name}: {stripped[:100]}")
                break
    return "\n".join(lines)
