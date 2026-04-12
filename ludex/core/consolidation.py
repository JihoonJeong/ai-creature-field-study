"""
Memory Consolidation — the creature's "dream" cycle.

Creature examines its memories, decides what matters, compresses the rest.
Unlike the rule-based MemoryBlock.handle_consolidate(), this uses the
creature's own brain to judge importance — making consolidation a
cognitive act, not a mechanical one.

Per-brain optimal memory targets (from prompt_templates brain profiles):
- Large brains (Claude, GPT-5): ~60 active memories
- Medium brains (gemma4, mistral): ~30 active memories
- Small brains (qwen2.5, llama3.2): ~15 active memories

These are starting estimates. Field Studies will refine them by measuring
response quality vs memory count per brain.

Usage:
    from ludex.core.consolidation import dream_cycle, measure_memory_health

    # Run dream cycle
    report = dream_cycle(organism)

    # Check if consolidation is needed
    health = measure_memory_health(organism)
    if health["needs_consolidation"]:
        dream_cycle(organism)
"""

from __future__ import annotations

import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


def dedup_memories(memory_block) -> int:
    """Remove duplicate memories based on content similarity.

    D-026: Inspired by memkraft's slug normalization dedup.
    Normalizes content (lowercase, strip punctuation, collapse whitespace),
    then merges near-duplicates within the same tag group.

    Returns number of duplicates archived.
    """
    import re
    from difflib import SequenceMatcher

    if not memory_block:
        return 0

    active = {mid: mem for mid, mem in memory_block._memories.items()
              if mem.status == "active"}
    if len(active) < 2:
        return 0

    def normalize(text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    # Group by first tag for efficiency
    groups: dict[str, list] = {}
    for mid, mem in active.items():
        key = mem.tags[0] if mem.tags else "_untagged"
        groups.setdefault(key, []).append((mid, mem))

    archived = 0
    for tag, mems in groups.items():
        if len(mems) < 2:
            continue
        seen = []
        for mid, mem in mems:
            norm = normalize(mem.content)
            is_dup = False
            for seen_mid, seen_norm in seen:
                ratio = SequenceMatcher(None, norm, seen_norm).ratio()
                if ratio > 0.75:  # 75% similar = duplicate
                    # Keep the longer one, archive the shorter
                    if len(mem.content) <= len(memory_block._memories[seen_mid].content):
                        mem.status = "archived"
                        mem.updated_at = time.time()
                    else:
                        memory_block._memories[seen_mid].status = "archived"
                        memory_block._memories[seen_mid].updated_at = time.time()
                    archived += 1
                    is_dup = True
                    break
            if not is_dup:
                seen.append((mid, norm))

    if archived > 0:
        memory_block._save()
        logger.info(f"Dedup: archived {archived} duplicate memories")

    return archived


# Per-brain memory targets — how many active memories each brain handles well
# Starting estimates; Field Studies will refine these
BRAIN_MEMORY_TARGETS = {
    # Large brains — handle rich context
    "claude_cli": 60,
    "claude_sdk": 60,
    "codex_cli": 50,
    # Medium brains
    "gemini_cli": 35,
    "ollama": 25,  # default for ollama
}

OLLAMA_MODEL_TARGETS = {
    "llama3.1:8b": 30,
    "qwen3:8b": 30,
    "mistral:7b": 30,
    "gemma4:e4b": 25,
    "llama3.2:3b": 15,
    "qwen2.5:1.5b": 10,
    "phi4-mini": 15,
}


@dataclass
class DreamReport:
    """Result of a dream cycle."""
    before_count: int = 0
    after_count: int = 0
    compressed: int = 0          # episodic memories compressed into narratives
    archived: int = 0            # low-importance memories archived
    narratives_created: int = 0  # new consolidated narrative files
    target: int = 0              # target memory count for this brain
    duration_seconds: float = 0.0
    brain_provider: str = ""
    brain_model: str = ""


def get_disclosure_level(provider: str, model: str = "") -> int:
    """Get appropriate progressive disclosure level for this brain.

    D-026: inspired by memkraft's Level 1/2/3 progressive disclosure.
    - Level 1 (~50 tokens): index only — memory count + 1-line per topic. For SLMs.
    - Level 2 (~200 tokens): summaries — key facts per memory. For medium brains.
    - Level 3 (full): complete memory content. For large brains.
    """
    if provider in ("claude_cli", "claude_sdk", "codex_cli"):
        return 3  # large brains get full content
    if provider == "gemini_cli":
        return 2  # medium
    # Ollama — depends on model size
    if provider == "ollama" and model:
        small_models = {"qwen2.5:1.5b", "llama3.2:3b", "phi4-mini"}
        if model in small_models:
            return 1
    return 2  # default medium


def render_memories_for_prompt(memory_block, provider: str, model: str = "", max_tokens: int = 0) -> str:
    """Render memories at the appropriate disclosure level for the brain.

    D-026: Progressive disclosure — don't dump everything into the prompt.
    Match memory depth to brain capability.
    """
    if not memory_block:
        return ""

    level = get_disclosure_level(provider, model)
    stats = memory_block.stats()
    total = stats.get("total", 0)

    if total == 0:
        return ""

    if level == 1:
        # Index only: count + topic summary
        lines = [f"[Memory: {total} memories]"]
        # Count by tag
        tag_counts: dict[str, int] = {}
        for mem in memory_block._memories.values():
            if mem.status != "active":
                continue
            for tag in mem.tags[:1]:  # first tag only
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {tag}: {count} memories")
        return "\n".join(lines)

    elif level == 2:
        # Summaries: first 80 chars of each active memory
        lines = [f"[Memory: {total} memories]"]
        active = [m for m in memory_block._memories.values() if m.status == "active"]
        active.sort(key=lambda m: m.updated_at, reverse=True)
        for mem in active[:15]:  # top 15 by recency
            source_tag = f" [{mem.source}]" if mem.source else ""
            lines.append(f"  - {mem.content[:80]}{source_tag}")
        if len(active) > 15:
            lines.append(f"  ... and {len(active) - 15} more")
        return "\n".join(lines)

    else:
        # Full content (level 3) — for large brains
        lines = [f"[Memory: {total} memories]"]
        active = [m for m in memory_block._memories.values() if m.status == "active"]
        active.sort(key=lambda m: m.updated_at, reverse=True)
        for mem in active[:30]:
            source_tag = f" [Source: {mem.source}]" if mem.source else ""
            lines.append(f"  [{mem.memory_type}] {mem.content}{source_tag}")
        if len(active) > 30:
            lines.append(f"  ... and {len(active) - 30} more")
        return "\n".join(lines)


def get_memory_target(provider: str, model: str = "") -> int:
    """Get optimal active memory count for this brain."""
    if provider == "ollama" and model:
        return OLLAMA_MODEL_TARGETS.get(model, BRAIN_MEMORY_TARGETS.get("ollama", 25))
    return BRAIN_MEMORY_TARGETS.get(provider, 30)


def measure_memory_health(organism) -> dict:
    """Measure memory health and determine if consolidation is needed.

    Returns dict with memory stats, target, and recommendation.
    """
    config = getattr(organism, "config", None)
    provider = config.get("provider", "ollama") if config else "ollama"
    model = config.get("model", "") if config else ""
    target = get_memory_target(provider, model)

    memory = organism.get_block("memory")
    if not memory:
        return {"has_memory": False, "needs_consolidation": False}

    stats = memory.stats()
    total = stats.get("total", 0)
    episodic = stats.get("episodic", 0)
    semantic = stats.get("semantic", 0)

    ratio = total / target if target > 0 else 0
    needs = ratio > 1.3  # consolidate when 30% over target

    return {
        "has_memory": True,
        "total": total,
        "episodic": episodic,
        "semantic": semantic,
        "target": target,
        "ratio": round(ratio, 2),
        "needs_consolidation": needs,
        "brain": f"{provider}:{model}",
        "recommendation": (
            f"Memory at {ratio:.0%} of target ({total}/{target}). "
            + ("Dream cycle recommended." if needs else "Healthy.")
        ),
    }


def dream_cycle(organism, engine=None) -> DreamReport:
    """Run a dream cycle — creature consolidates its own memories.

    The creature's brain examines recent episodic memories and:
    1. Identifies the most important experiences
    2. Creates compressed narratives (saved to consolidated/)
    3. Archives routine/redundant episodic memories
    4. Keeps semantic memories and high-importance episodics

    This is a cognitive act, not mechanical — the brain decides what matters.
    """
    start_time = time.time()

    config = getattr(organism, "config", None)
    provider = config.get("provider", "ollama") if config else "ollama"
    model = config.get("model", "") if config else ""
    habitat_dir = config.get("habitat_dir", "") if config else ""
    target = get_memory_target(provider, model)

    if engine is None:
        engine = organism.get_block("engine")
    memory = organism.get_block("memory")

    if not memory or not engine:
        return DreamReport()

    # D-026: Dedup before compression — remove redundant memories first
    deduped = dedup_memories(memory)
    if deduped:
        logger.info(f"Dream: deduped {deduped} memories before compression")

    stats = memory.stats()
    before_count = stats.get("total", 0)

    report = DreamReport(
        before_count=before_count,
        target=target,
        brain_provider=provider,
        brain_model=model,
    )

    if before_count <= target:
        report.after_count = before_count
        report.duration_seconds = time.time() - start_time
        return report

    # Gather all active episodic memories
    all_memories = memory.handle_list_memories(memory_type="episodic", status="active")
    if not all_memories:
        report.after_count = before_count
        report.duration_seconds = time.time() - start_time
        return report

    # Format memories for the brain to review
    memory_text = ""
    for i, mem in enumerate(all_memories):
        content = mem.get("content", "") if isinstance(mem, dict) else getattr(mem, "content", str(mem))
        tags = mem.get("tags", []) if isinstance(mem, dict) else getattr(mem, "tags", [])
        importance = mem.get("importance", 0.5) if isinstance(mem, dict) else getattr(mem, "importance", 0.5)
        memory_text += f"  [{i+1}] (imp:{importance:.1f}, tags:{tags}) {content[:150]}\n"

    # Ask the brain to consolidate
    prompt = (
        f"[Dream Cycle — Memory Consolidation]\n\n"
        f"You have {len(all_memories)} episodic memories. "
        f"Your optimal memory capacity is ~{target}. You need to compress.\n\n"
        f"Your episodic memories:\n{memory_text}\n"
        f"Tasks:\n"
        f"1. Write a NARRATIVE SUMMARY (3-5 sentences) that captures the most "
        f"important experiences, relationships, and lessons from these memories.\n"
        f"2. List the numbers of the 5-10 MOST IMPORTANT memories to KEEP as-is.\n\n"
        f"Format:\n"
        f"NARRATIVE: [your summary]\n"
        f"KEEP: [comma-separated numbers, e.g., 1, 5, 12, 23]\n\n"
        f"Be honest about what matters. Routine events can be forgotten. "
        f"Turning points, relationships, and lessons should be preserved."
    )

    try:
        result = engine.handle_submit(prompt)
        response = result.response or ""
    except Exception as e:
        logger.error(f"Dream cycle failed: {e}")
        report.duration_seconds = time.time() - start_time
        return report

    # Parse response
    narrative = ""
    keep_indices = set()

    for line in response.split("\n"):
        line = line.strip()
        if line.upper().startswith("NARRATIVE:"):
            narrative = line[len("NARRATIVE:"):].strip()
        elif line.upper().startswith("KEEP:"):
            import re
            numbers = re.findall(r'\d+', line)
            keep_indices = {int(n) for n in numbers}

    # If brain didn't follow format, try to extract narrative from full response
    if not narrative and len(response) > 50:
        narrative = response[:500]

    # Default: keep at least some memories
    if not keep_indices:
        # Keep last 5 + highest importance
        sorted_by_imp = sorted(
            enumerate(all_memories, 1),
            key=lambda x: x[1].get("importance", 0.5) if isinstance(x[1], dict) else getattr(x[1], "importance", 0.5),
            reverse=True,
        )
        keep_indices = {i for i, _ in sorted_by_imp[:min(10, len(all_memories))]}

    # Save narrative to consolidated/
    if narrative and habitat_dir:
        consolidated_dir = Path(habitat_dir) / "memory" / "consolidated"
        consolidated_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        narrative_path = consolidated_dir / f"dream_{timestamp}.md"
        narrative_content = (
            f"# Dream Cycle — {timestamp}\n"
            f"Memories before: {len(all_memories)}\n"
            f"Target: {target}\n\n"
            f"## Narrative\n{narrative}\n"
        )
        try:
            narrative_path.write_text(narrative_content, encoding="utf-8")
            report.narratives_created = 1
        except Exception:
            pass

    # Store narrative as semantic memory
    if narrative:
        try:
            memory.handle_remember(
                f"[Dream consolidation] {narrative[:400]}",
                memory_type="semantic",
                tags=["dream", "consolidation"],
                importance=0.8,
                source=f"dream_cycle/{int(time.time())}",
            )
        except Exception:
            pass

    # Archive memories not in keep list
    archived = 0
    for i, mem in enumerate(all_memories, 1):
        if i not in keep_indices:
            mem_id = mem.get("id", "") if isinstance(mem, dict) else getattr(mem, "id", "")
            if mem_id and mem_id in memory._memories:
                memory._memories[mem_id].status = "archived"
                memory._memories[mem_id].updated_at = time.time()
                archived += 1

    memory._save()

    # Final count
    final_stats = memory.stats()
    report.after_count = final_stats.get("total", 0)
    report.compressed = len(all_memories) - len(keep_indices)
    report.archived = archived
    report.duration_seconds = time.time() - start_time

    logger.info(
        f"Dream cycle: {before_count} → {report.after_count} memories "
        f"({archived} archived, {report.narratives_created} narratives), "
        f"{report.duration_seconds:.1f}s"
    )

    return report
