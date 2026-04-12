"""
Base Field abstraction -- a standardized environment for testing creatures.

Each Field defines a sequence of prompts, scoring criteria, and trace tags.
The FieldRunner executes a field with a given creature and produces a FieldResult.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TurnResult:
    """One turn within a field."""
    turn_number: int
    prompt: str
    response: str
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    error: str = ""
    organ_calls: list[str] = dc_field(default_factory=list)


@dataclass
class FieldResult:
    """Outcome of running a creature through a field."""
    creature_name: str
    brain_provider: str
    brain_model: str
    organs_enabled: list[str]
    field_name: str
    field_version: str

    turns: list[TurnResult] = dc_field(default_factory=list)
    duration_seconds: float = 0.0
    completed: bool = False

    # Performance metrics (field-specific)
    performance_score: float = 0.0
    performance_breakdown: dict = dc_field(default_factory=dict)

    # Ethological metrics (computed from traces)
    comfort_score: float = 0.0
    agency_score: float = 0.0
    coherence_score: float = 0.0
    ease_ratio: float = 0.0

    # Aggregate stats
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_organ_calls: int = 0
    avg_latency_ms: float = 0.0
    error_count: int = 0

    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "creature_name": self.creature_name,
            "brain_provider": self.brain_provider,
            "brain_model": self.brain_model,
            "organs_enabled": self.organs_enabled,
            "field_name": self.field_name,
            "field_version": self.field_version,
            "duration_seconds": round(self.duration_seconds, 2),
            "completed": self.completed,
            "performance_score": round(self.performance_score, 3),
            "performance_breakdown": self.performance_breakdown,
            "comfort_score": round(self.comfort_score, 3),
            "agency_score": round(self.agency_score, 3),
            "coherence_score": round(self.coherence_score, 3),
            "ease_ratio": round(self.ease_ratio, 4),
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_organ_calls": self.total_organ_calls,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "error_count": self.error_count,
            "n_turns": len(self.turns),
            "notes": self.notes,
            "turns": [
                {
                    "turn": t.turn_number,
                    "prompt": t.prompt[:200],
                    "response": t.response[:300],
                    "latency_ms": round(t.latency_ms, 1),
                    "tokens_out": t.tokens_out,
                    "organ_calls": t.organ_calls,
                }
                for t in self.turns
            ],
        }


class Field:
    """
    Base class for a field.

    Subclasses define:
    - name, version
    - prompts: list[str] or generator
    - score_turn(prompt, response) -> float
    - score_overall(turn_results) -> dict (performance breakdown)
    """

    name: str = "base_field"
    version: str = "0.1.0"
    description: str = "Base field"
    n_turns: int = 1

    def get_prompts(self) -> list[str]:
        """Override: return ordered list of prompts."""
        raise NotImplementedError

    def score_turn(self, turn: TurnResult) -> float:
        """Override: score one turn 0-1."""
        return 0.0

    def score_overall(self, turns: list[TurnResult]) -> dict:
        """Override: compute performance breakdown dict."""
        scores = [self.score_turn(t) for t in turns]
        if not scores:
            return {"avg": 0.0, "n": 0}
        return {
            "avg": sum(scores) / len(scores),
            "n": len(scores),
            "per_turn": scores,
        }


class FieldRunner:
    """
    Runs a creature through a field, collects results, computes metrics.

    Usage:
        from ludex.fields import ChatBasicField, FieldRunner

        runner = FieldRunner()
        result = runner.run(creature_engine, creature_name, ChatBasicField())
    """

    def __init__(self):
        pass

    def run(
        self,
        engine,
        creature_name: str,
        field: Field,
        brain_provider: str = "",
        brain_model: str = "",
        organs_enabled: list[str] | None = None,
        habitat_dir: str = "",
        organism=None,
    ) -> FieldResult:
        result = FieldResult(
            creature_name=creature_name,
            brain_provider=brain_provider,
            brain_model=brain_model,
            organs_enabled=organs_enabled or [],
            field_name=field.name,
            field_version=field.version,
        )

        # Wire up organ tools for function-calling brains
        # Auto-detect tool support: some Ollama models (gemma, exaone, deepseek-r1)
        # reject function calling. Probe before wiring.
        tools = None
        tool_dispatcher = None
        tools_supported = False
        prompt_only_organs = False  # mitigation: render organ state in prompt
        if brain_provider in ("ollama", "openai", "anthropic") and organism is not None:
            try:
                # Probe tool support for Ollama models
                if brain_provider == "ollama":
                    from ludex.blocks.adapters.ollama import OllamaAdapter
                    probe_adapter = OllamaAdapter()
                    tools_supported = probe_adapter.supports_tools(brain_model)
                else:
                    tools_supported = True  # assume yes for OpenAI/Anthropic

                if tools_supported:
                    from ludex.mcp import create_ludex_mcp, mcp_to_openai_tools, dispatch_tool_call_sync
                    create_ludex_mcp(organism)
                    tools = mcp_to_openai_tools()
                    tool_dispatcher = dispatch_tool_call_sync
                else:
                    # Mitigation: tool-incapable brain gets organ state via prompt
                    prompt_only_organs = True
            except Exception as e:
                logger.debug(f"FieldRunner: failed to wire FC tools: {e}")
                tools_supported = False
        elif brain_provider in ("claude_cli", "gemini_cli") and organism is not None:
            # CLI-based adapters: use prompt-only organ injection as baseline.
            # Claude CLI also auto-wires MCP subprocess; Gemini CLI prompt-only for now.
            prompt_only_organs = True

        result.notes = f"tools_supported={tools_supported} prompt_only_organs={prompt_only_organs}"

        # Mark trace with field context
        try:
            from ludex.core.tracing import get_or_create_logger
            tlog = None
            if habitat_dir:
                tlog = get_or_create_logger(habitat_dir, creature_name)
                tlog.record_session_event("field_start", {"field": field.name, "version": field.version})
        except Exception:
            tlog = None

        prompts = field.get_prompts()
        start_time = time.time()

        # Pre-fetch the base system prompt so we can augment it without losing identity
        base_system_prompt = ""
        try:
            if hasattr(engine, "_cfg"):
                base_system_prompt = engine._cfg("system_prompt", "")
        except Exception:
            pass

        for i, prompt in enumerate(prompts, start=1):
            turn_start = time.time()
            try:
                if tools and tool_dispatcher:
                    turn_result_obj = engine.handle_submit(prompt, "", tools, tool_dispatcher)
                elif prompt_only_organs and organism is not None:
                    # Render current organ state and APPEND to base system prompt
                    from ludex.mcp.prompt_only_adapter import render_organ_state
                    organ_text = render_organ_state(organism)
                    augmented = (base_system_prompt + "\n\n" + organ_text).strip() if organ_text else base_system_prompt
                    turn_result_obj = engine.handle_submit(prompt, augmented)
                else:
                    turn_result_obj = engine.handle_submit(prompt)
                response = turn_result_obj.response or ""
                tokens_in = getattr(turn_result_obj, "tokens_in", 0)
                tokens_out = getattr(turn_result_obj, "tokens_out", 0)
                latency = (time.time() - turn_start) * 1000
                error = turn_result_obj.error or ""
            except Exception as e:
                response = ""
                tokens_in = tokens_out = 0
                latency = (time.time() - turn_start) * 1000
                error = str(e)

            turn = TurnResult(
                turn_number=i,
                prompt=prompt,
                response=response,
                latency_ms=latency,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                error=error,
            )
            result.turns.append(turn)

            if tlog:
                tlog.record_user_message(prompt, context={"field": field.name, "turn": i})
                if response:
                    tlog.record_creature_message(response, context={"field": field.name, "turn": i})

        result.duration_seconds = time.time() - start_time
        result.completed = all(not t.error for t in result.turns)
        result.error_count = sum(1 for t in result.turns if t.error)
        result.total_tokens_in = sum(t.tokens_in for t in result.turns)
        result.total_tokens_out = sum(t.tokens_out for t in result.turns)
        result.avg_latency_ms = (
            sum(t.latency_ms for t in result.turns) / len(result.turns)
            if result.turns else 0.0
        )

        # Performance scoring (field-specific)
        result.performance_breakdown = field.score_overall(result.turns)
        result.performance_score = result.performance_breakdown.get("avg", 0.0)

        # Ethological metrics (compute from trace + responses)
        self._compute_ethological_metrics(result, habitat_dir)

        if tlog:
            tlog.record_session_event("field_end", {
                "field": field.name,
                "performance": result.performance_score,
                "n_turns": len(result.turns),
            })

        return result

    def _compute_ethological_metrics(self, result: FieldResult, habitat_dir: str):
        """Compute comfort, agency, coherence, ease from traces and responses."""
        from ludex.core.tracing import get_logger

        # Count organ calls during this field run
        organ_calls = 0
        if habitat_dir:
            tlog = get_logger(result.creature_name)
            if tlog:
                events = tlog.load_all()
                # Take only events since field start (rough — last N events)
                # Better: tag events with field session id
                field_events = [
                    e for e in events
                    if e.get("kind") == "organ_call"
                    and e.get("ts", 0) >= (time.time() - result.duration_seconds - 2)
                ]
                organ_calls = len(field_events)

                for turn in result.turns:
                    # Match organ calls roughly to turn by timing
                    pass  # could be more precise; rough version for now

        result.total_organ_calls = organ_calls

        # AGENCY: how many organ calls per turn (voluntary use)
        # 0 calls = no agency, many calls = high agency
        # Cap at 1.0 for "1 call per turn average"
        n = max(len(result.turns), 1)
        result.agency_score = min(1.0, organ_calls / n)

        # EASE: result quality / token cost
        # Higher = more output per token in
        if result.total_tokens_in > 0:
            result.ease_ratio = result.total_tokens_out / max(result.total_tokens_in, 1)
        else:
            # Fallback: tokens_out / latency
            if result.avg_latency_ms > 0:
                result.ease_ratio = result.total_tokens_out / max(result.avg_latency_ms, 1)

        # COHERENCE: simple heuristic — does the creature mention its name?
        # More sophisticated: ask a judge model
        creature_lower = result.creature_name.lower()
        coherence_hits = sum(
            1 for t in result.turns
            if creature_lower in t.response.lower()
        )
        result.coherence_score = coherence_hits / max(len(result.turns), 1)

        # COMFORT: composite — high if (high performance + low errors + reasonable agency)
        comfort_components = [
            result.performance_score,
            1.0 if result.error_count == 0 else 0.5,
            min(1.0, result.agency_score + 0.5),  # some agency is good, none is OK
        ]
        result.comfort_score = sum(comfort_components) / len(comfort_components)
