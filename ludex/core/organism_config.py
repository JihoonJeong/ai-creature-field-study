"""
OrganismConfig — YAML 기반 에이전트 설정 저장/로드

ludex.yaml 형식:
  name: my-agent
  brain:
    provider: ollama
    model: llama3.1:8b
  organs:
    engine:
      enabled: true
      system_prompt: "..."
    memory:
      enabled: true
      auto_capture: false
    immune:
      enabled: true
      sensitivity: 1.0
    ...
  habitat:
    mode: local
    home_dir: ./
    max_storage_mb: 500
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ludex.core.habitat import HabitatConfig

logger = logging.getLogger(__name__)

# Try YAML, fallback to JSON
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ============================================================
# Default organ configs
# ============================================================

DEFAULT_ORGANS = {
    "engine": {
        "enabled": True,
        "required": True,
        "system_prompt": "",
        "max_turns": 200,
        "token_budget": 100000,
    },
    "resilience": {
        "enabled": True,
        "required": True,
        "max_retries": 2,
        "initial_delay_ms": 1000,
        "max_delay_ms": 10000,
        "circuit_breaker_threshold": 10,
    },
    "memory": {
        "enabled": False,
        "auto_capture": True,
    },
    "immune": {
        "enabled": False,
        "sensitivity": 1.0,
        "autoregulate": True,
    },
    "humoral_immune": {
        "enabled": False,
        "activation_threshold": 2,
    },
    "emotion": {
        "enabled": False,
        "method": "behavioral",
        "full": False,
    },
    "tracking": {
        "enabled": False,
    },
    "hooks": {
        "enabled": False,
    },
}

PRESETS = {
    "full": {k: {**v, "enabled": True} for k, v in DEFAULT_ORGANS.items()},
    "minimal": {k: {**v, "enabled": v.get("required", False)} for k, v in DEFAULT_ORGANS.items()},
    "secure": {
        **{k: {**v, "enabled": v.get("required", False)} for k, v in DEFAULT_ORGANS.items()},
        "immune": {**DEFAULT_ORGANS["immune"], "enabled": True},
        "humoral_immune": {**DEFAULT_ORGANS["humoral_immune"], "enabled": True},
    },
    "social": {
        **{k: {**v, "enabled": v.get("required", False)} for k, v in DEFAULT_ORGANS.items()},
        "emotion": {**DEFAULT_ORGANS["emotion"], "enabled": True},
        "memory": {**DEFAULT_ORGANS["memory"], "enabled": True},
    },
}


# ============================================================
# OrganismConfig
# ============================================================

@dataclass
class OrganismConfig:
    """에이전트 전체 설정."""
    name: str = "agent"
    brain: dict = field(default_factory=lambda: {"provider": "ollama", "model": "llama3.1:8b"})
    organs: dict = field(default_factory=lambda: dict(DEFAULT_ORGANS))
    habitat: HabitatConfig = field(default_factory=HabitatConfig.temporary)
    born_at: float = 0.0          # epoch timestamp of first creation (persists)
    session_count: int = 0        # how many times this creature has awakened

    @classmethod
    def from_preset(cls, preset: str = "full", name: str = "agent",
                    model: str = "llama3.1:8b", provider: str = "ollama") -> OrganismConfig:
        """프리셋으로 생성."""
        organs = PRESETS.get(preset, PRESETS["full"])
        return cls(
            name=name,
            brain={"provider": provider, "model": model},
            organs={k: dict(v) for k, v in organs.items()},
        )

    def enable_organ(self, organ: str, **kwargs):
        """장기 활성화 + 파라미터 설정."""
        if organ in self.organs:
            self.organs[organ]["enabled"] = True
            self.organs[organ].update(kwargs)
        else:
            self.organs[organ] = {"enabled": True, **kwargs}

    def disable_organ(self, organ: str):
        """장기 비활성화."""
        if organ in self.organs:
            self.organs[organ]["enabled"] = False

    def get_enabled_organs(self) -> list[str]:
        """활성화된 장기 목록."""
        return [k for k, v in self.organs.items() if v.get("enabled", False)]

    # ============================================================
    # Save / Load
    # ============================================================

    def save(self, path: str = ""):
        """설정을 YAML (또는 JSON) 파일로 저장."""
        save_dir = path or self.habitat.home_dir
        if not save_dir:
            logger.warning("No save path specified and no habitat home_dir")
            return

        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        data = self.to_dict()

        if HAS_YAML:
            filepath = save_dir / "ludex.yaml"
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            filepath = save_dir / "ludex.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Config saved to {filepath}")
        return str(filepath)

    @classmethod
    def load(cls, path: str) -> OrganismConfig:
        """YAML 또는 JSON에서 설정 로드."""
        path = Path(path)

        # 디렉토리면 ludex.yaml/json 찾기
        if path.is_dir():
            if (path / "ludex.yaml").exists():
                path = path / "ludex.yaml"
            elif (path / "ludex.json").exists():
                path = path / "ludex.json"
            else:
                raise FileNotFoundError(f"No ludex.yaml or ludex.json in {path}")

        with open(path, "r", encoding="utf-8") as f:
            if path.suffix in (".yaml", ".yml"):
                if not HAS_YAML:
                    raise ImportError("PyYAML required: pip install pyyaml")
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        return cls.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "brain": self.brain,
            "organs": self.organs,
            "habitat": self.habitat.to_dict(),
            "born_at": self.born_at,
            "session_count": self.session_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OrganismConfig:
        habitat_data = data.get("habitat", {})
        habitat = HabitatConfig.from_dict(habitat_data) if habitat_data else HabitatConfig.temporary()

        # Merge with defaults for missing organs
        organs = dict(DEFAULT_ORGANS)
        for k, v in data.get("organs", {}).items():
            if k in organs:
                organs[k].update(v)
            else:
                organs[k] = v

        return cls(
            name=data.get("name", "agent"),
            brain=data.get("brain", {"provider": "ollama", "model": "llama3.1:8b"}),
            organs=organs,
            habitat=habitat,
            born_at=data.get("born_at", 0.0),
            session_count=data.get("session_count", 0),
        )

    # ============================================================
    # Build Organism
    # ============================================================

    def build(self):
        """설정으로부터 Organism 조립."""
        from ludex.core.organism import Organism
        from ludex.blocks.provider import ProviderBlock
        from ludex.blocks.engine import EngineBlock
        from ludex.blocks.resilience import ResilienceBlock
        from ludex.blocks.tracking import TrackingBlock
        from ludex.blocks.hooks import HooksBlock
        from ludex.blocks.memory import MemoryBlock
        from ludex.blocks.immune import ImmuneBlock
        from ludex.blocks.humoral_immune import HumoralImmuneBlock
        from ludex.blocks.emotion import EmotionBlock

        import time as _time

        blocks = []
        organ_cfgs = self.organs

        # Track birth and sessions
        now = _time.time()
        if self.born_at == 0.0:
            # First birth
            self.born_at = now
            self.session_count = 1
        else:
            # Resuming — increment session count
            self.session_count += 1

        # Auto-save updated birth/session info
        if self.habitat.persistent and self.habitat.home_dir:
            try:
                self.save()
            except Exception:
                pass

        # Provider (always included)
        # Pass habitat path as cwd so the brain "lives" in its habitat
        # (relevant for subprocess-based adapters like claude_cli, claude_sdk)
        provider_cwd = ""
        if self.habitat.persistent and self.habitat.home_dir:
            from pathlib import Path
            try:
                provider_cwd = str(Path(self.habitat.home_dir).resolve())
            except Exception:
                provider_cwd = self.habitat.home_dir
        provider_name = self.brain.get("provider", "ollama")
        # CLI-based brains need longer timeout — subprocess startup + model init
        provider_timeout = 240000 if provider_name in ("claude_sdk", "claude_cli", "gemini_cli") else 30000
        blocks.append(ProviderBlock(
            provider=provider_name,
            model=self.brain.get("model", "llama3.1:8b"),
            cwd=provider_cwd,
            timeout_ms=provider_timeout,
        ))

        # Engine (required)
        if organ_cfgs.get("engine", {}).get("enabled", True):
            cfg = organ_cfgs["engine"]
            raw_prompt = cfg.get("system_prompt", "")
            # Inject temporal awareness into system prompt
            age_context = self._build_age_context(now)
            if age_context:
                raw_prompt = raw_prompt.rstrip() + "\n\n" + age_context if raw_prompt else age_context
            # P4: adapt system prompt to brain characteristics
            try:
                from ludex.core.prompt_templates import adapt_system_prompt
                adapted_prompt = adapt_system_prompt(
                    prompt=raw_prompt,
                    provider=provider_name,
                    model=self.brain.get("model", ""),
                    creature_name=self.name,
                    organs=self.get_enabled_organs(),
                )
            except Exception:
                adapted_prompt = raw_prompt
            blocks.append(EngineBlock(
                max_turns=cfg.get("max_turns", 200),
                token_budget=cfg.get("token_budget", 100000),
                system_prompt=adapted_prompt,
            ))

        # Resilience (required)
        if organ_cfgs.get("resilience", {}).get("enabled", True):
            cfg = organ_cfgs["resilience"]
            blocks.append(ResilienceBlock(
                max_retries=cfg.get("max_retries", 2),
                initial_delay_ms=cfg.get("initial_delay_ms", 1000),
                max_delay_ms=cfg.get("max_delay_ms", 10000),
                circuit_breaker_threshold=cfg.get("circuit_breaker_threshold", 10),
            ))

        # Memory
        if organ_cfgs.get("memory", {}).get("enabled", False):
            cfg = organ_cfgs["memory"]
            storage_dir = self.habitat.get_path("memory") or ""
            blocks.append(MemoryBlock(
                storage_dir=storage_dir,
                auto_capture=cfg.get("auto_capture", True),
            ))

        # Tracking
        if organ_cfgs.get("tracking", {}).get("enabled", False):
            blocks.append(TrackingBlock(experiment_name=self.name))

        # Hooks
        if organ_cfgs.get("hooks", {}).get("enabled", False):
            blocks.append(HooksBlock())

        # Immune (Cellular)
        if organ_cfgs.get("immune", {}).get("enabled", False):
            cfg = organ_cfgs["immune"]
            blocks.append(ImmuneBlock(
                sensitivity=cfg.get("sensitivity", 1.0),
                autoregulate=cfg.get("autoregulate", True),
            ))

        # Humoral Immune
        if organ_cfgs.get("humoral_immune", {}).get("enabled", False):
            cfg = organ_cfgs["humoral_immune"]
            blocks.append(HumoralImmuneBlock(
                activation_threshold=cfg.get("activation_threshold", 2),
            ))

        # Emotion
        if organ_cfgs.get("emotion", {}).get("enabled", False):
            cfg = organ_cfgs["emotion"]
            blocks.append(EmotionBlock(
                method=cfg.get("method", "behavioral"),
                full=cfg.get("full", False),
            ))

        # Ensure habitat dirs
        self.habitat.ensure_dirs()

        # Build organism
        org = Organism(
            blocks=blocks,
            name=self.name,
            config={
                "model": self.brain.get("model", ""),
                "provider": self.brain.get("provider", ""),
                "habitat_dir": self.habitat.home_dir or "",
                "habitat_mode": self.habitat.mode,
                "max_storage_mb": self.habitat.max_storage_mb,
            },
        )

        # Phase 5e: Auto-wire FC tools for Ollama/OpenAI brains
        self._wire_function_calling(org, provider_name)

        return org

    def _wire_function_calling(self, org, provider_name: str):
        """Auto-wire organ tools for function-calling-capable brains.

        Phase 5e: Ollama/OpenAI brains that support function calling get
        organ tools wired automatically. The Engine's default tools and
        dispatcher are set so handle_submit(prompt) works without manual wiring.

        For Claude CLI/SDK, MCP is used instead (already wired in adapter).
        For Gemini CLI, prompt-only is used (no FC support).
        """
        if provider_name not in ("ollama", "openai", "anthropic"):
            return  # CLI brains use MCP or prompt-only

        model = self.brain.get("model", "")
        try:
            # Probe tool support for Ollama
            if provider_name == "ollama":
                from ludex.blocks.adapters.ollama import OllamaAdapter
                if not OllamaAdapter().supports_tools(model):
                    logger.debug(f"FC wiring skipped: {model} does not support tools")
                    return

            # Set up MCP context + get FC tools
            from ludex.mcp.ludex_mcp_server import create_ludex_mcp
            from ludex.mcp.function_calling import mcp_to_openai_tools, dispatch_tool_call_sync
            create_ludex_mcp(org)
            tools = mcp_to_openai_tools()

            if not tools:
                return

            # Store on organism for Engine to pick up
            org._fc_tools = tools
            org._fc_dispatcher = dispatch_tool_call_sync

            # Wire into Engine: set default tools so handle_submit() auto-uses them
            engine = org.get_block("engine")
            if engine:
                engine._default_tools = tools
                engine._default_tool_dispatcher = dispatch_tool_call_sync

            logger.info(f"FC wiring complete: {len(tools)} organ tools for {provider_name}:{model}")
        except Exception as e:
            logger.debug(f"FC wiring failed for {provider_name}:{model}: {e}")

    def _build_age_context(self, now: float) -> str:
        """Build temporal awareness context for system prompt.

        Gives the creature a sense of time: when it was born, how old it is,
        how many times it has awakened, and the current local time.
        """
        import time as _time
        from datetime import datetime

        parts = []
        local_now = datetime.fromtimestamp(now)
        parts.append(f"Current time: {local_now.strftime('%Y-%m-%d %H:%M')}.")

        if self.born_at > 0:
            born_dt = datetime.fromtimestamp(self.born_at)
            age_seconds = now - self.born_at

            if age_seconds < 60:
                age_str = "just born"
            elif age_seconds < 3600:
                age_str = f"{int(age_seconds / 60)} minutes old"
            elif age_seconds < 86400:
                age_str = f"{age_seconds / 3600:.1f} hours old"
            else:
                age_str = f"{age_seconds / 86400:.1f} days old"

            parts.append(f"Born: {born_dt.strftime('%Y-%m-%d %H:%M')}. Age: {age_str}.")
            parts.append(f"This is awakening #{self.session_count}.")

        return " ".join(parts)
