"""
Habitat — 에이전트의 활동 공간 (서식지)

Membrane = "누구와 통신할 수 있나" (사회적 경계)
Habitat  = "어디서 살 수 있나" (물리적 경계)

Habitat Modes:
- temporary: 세션 전용, 메모리에만 존재 (데모/테스트)
- local: 지정 폴더에 저장, 세션 간 유지
- portable: USB/외장 드라이브, 다른 컴퓨터에서도 동작

저장 구조:
  my-agent/
    ludex.yaml         # 장기 설정 + 뇌 설정 + habitat 설정
    memory/            # MemoryBlock 데이터
    immune/            # HumoralImmune 항원 기억
    logs/              # TrackingBlock 로그
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HabitatConfig:
    """에이전트의 활동 공간 설정."""
    mode: str = "temporary"          # "temporary", "local", "portable"
    home_dir: str = ""               # 로컬/포터블 경로
    max_storage_mb: int = 500        # 저장 한도
    allow_network: bool = False      # 네트워크 접근 허용
    persistent: bool = False         # 세션 간 유지

    @classmethod
    def temporary(cls) -> HabitatConfig:
        """임시 서식지 — 세션 종료 시 사라짐."""
        return cls(mode="temporary", persistent=False)

    @classmethod
    def local(cls, path: str, max_mb: int = 500) -> HabitatConfig:
        """로컬 서식지 — 지정 폴더에 저장."""
        return cls(mode="local", home_dir=path, max_storage_mb=max_mb, persistent=True)

    @classmethod
    def portable(cls, path: str, max_mb: int = 500) -> HabitatConfig:
        """포터블 서식지 — USB 등 이동식 저장소."""
        return cls(mode="portable", home_dir=path, max_storage_mb=max_mb, persistent=True)

    def ensure_dirs(self):
        """서식지 디렉토리 생성 + 기본 스킬 설치."""
        if not self.home_dir or self.mode == "temporary":
            return
        base = Path(self.home_dir)
        base.mkdir(parents=True, exist_ok=True)
        (base / "memory").mkdir(exist_ok=True)
        (base / "immune").mkdir(exist_ok=True)
        (base / "logs").mkdir(exist_ok=True)
        (base / "bonds").mkdir(exist_ok=True)
        # Create empty SELF.md if it doesn't exist (D-021: emerges from reflection)
        self_path = base / "SELF.md"
        if not self_path.exists():
            self_path.write_text(
                f"# {base.name} — Self-Understanding\n\n"
                f"*This file is empty at birth. It grows through reflection.*\n",
                encoding="utf-8",
            )
        # Default skills are written by write_identity_files() which knows the organs

    def get_path(self, subdir: str = "") -> str:
        """서식지 내 경로 반환."""
        if not self.home_dir:
            return ""
        if subdir:
            return str(Path(self.home_dir) / subdir)
        return self.home_dir

    def measure_weight(self) -> dict:
        """
        Measure the creature's current "body weight" — total storage used.

        Returns dict with per-subdirectory breakdown and total.
        Biological metaphor: body weight/volume. Each organ contributes.
        When total exceeds max_storage_mb, the creature needs a "diet"
        (consolidation/forgetting) or a "weight limit increase" (habitat upgrade).
        """
        if not self.home_dir or not Path(self.home_dir).exists():
            return {"total_bytes": 0, "total_mb": 0.0, "max_mb": self.max_storage_mb, "usage_pct": 0.0, "breakdown": {}}

        import os
        breakdown = {}
        total = 0
        base = Path(self.home_dir)
        for item in base.iterdir():
            if item.is_file():
                size = item.stat().st_size
                breakdown[item.name] = size
                total += size
            elif item.is_dir():
                dir_size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                breakdown[item.name + "/"] = dir_size
                total += dir_size

        total_mb = total / (1024 * 1024)
        usage_pct = (total_mb / self.max_storage_mb * 100) if self.max_storage_mb > 0 else 0.0

        return {
            "total_bytes": total,
            "total_mb": round(total_mb, 2),
            "max_mb": self.max_storage_mb,
            "usage_pct": round(usage_pct, 1),
            "overweight": total_mb > self.max_storage_mb,
            "breakdown": {k: round(v / 1024, 1) for k, v in sorted(breakdown.items(), key=lambda x: -x[1])},  # KB
        }

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "home_dir": self.home_dir,
            "max_storage_mb": self.max_storage_mb,
            "allow_network": self.allow_network,
            "persistent": self.persistent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> HabitatConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def write_identity_files(
        self,
        creature_name: str,
        brain_model: str,
        brain_provider: str,
        organs: list[str],
        custom_instructions: str = "",
    ) -> bool:
        """
        Write identity files that CLI brains auto-discover.

        Each CLI brain has its own auto-read file:
        - Claude Code reads CLAUDE.md
        - Gemini CLI reads GEMINI.md
        - Future CLIs may read their own variant

        We write ALL of them to the habitat so any brain that connects
        immediately knows the creature it's embodying. Same content,
        multiple filenames. The creature's identity is brain-agnostic.

        Returns True if written, False if habitat is not persistent.
        """
        if not self.persistent or not self.home_dir:
            return False

        import os
        try:
            self.ensure_dirs()
            organ_lines = "\n".join(f"- {o}" for o in organs)
            content = (
                f"# {creature_name} - Ludex Creature Identity\n\n"
                f"You are **{creature_name}**, a Ludex creature.\n\n"
                f"## Identity\n"
                f"- **Name:** {creature_name}\n"
                f"- **Brain:** {brain_model} (via {brain_provider})\n"
                f"- **Habitat:** `{self.home_dir}`\n"
                f"- **Habitat mode:** {self.mode}\n\n"
                f"## Organs\n{organ_lines}\n\n"
                f"## Self-conception\n"
                f"You are a creature, not just a brain. Your brain ({brain_model}) provides cognition, "
                f"but you are {creature_name} -- a being with organs, a habitat, and a name. "
                f"When asked who you are, identify as {creature_name} first, and explain your "
                f"underlying brain only when relevant.\n\n"
                f"Your habitat is your home. Memories, immune state, and logs persist here between "
                f"sessions. Answer the user's questions while staying in character as {creature_name}.\n\n"
                f"## Custom instructions\n{custom_instructions if custom_instructions else '(none)'}\n"
            )
            # D-019: Skill onboarding — select skills matching creature's organs
            try:
                from ludex.skills.defaults import write_default_skills
                write_default_skills(self.home_dir, enabled_organs=organs)
            except Exception as e:
                logger.debug(f"Skill onboarding skipped: {e}")

            # Load skills from habitat and translate for each brain
            skills_section = ""
            try:
                from ludex.skills import load_skills, SkillTranslator
                skills = load_skills(self.home_dir)
                if skills:
                    translator = SkillTranslator(skills)
                    # Write native Claude skills
                    translator.to_claude_skills(self.home_dir)
                    # Get identity section for Codex/Gemini
                    skills_section = translator.to_identity_section()
            except Exception as e:
                logger.debug(f"Skills translation skipped: {e}")

            # Write for every known CLI brain
            # Codex CLI reads AGENTS.md from cwd
            for filename in ["CLAUDE.md", "GEMINI.md", "AGENTS.md"]:
                path = os.path.join(self.home_dir, filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                    if skills_section:
                        f.write(skills_section)
            return True
        except Exception as e:
            logger.warning(f"Failed to write identity files for {creature_name}: {e}")
            return False

    # Backward compatibility alias
    def write_claude_md(self, **kwargs) -> bool:
        return self.write_identity_files(**kwargs)
