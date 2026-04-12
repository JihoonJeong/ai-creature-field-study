# Diverged from ludex/ludex/blocks/provider.py @ 65e765d (2026-04-10).
# Public repo supports only claude_cli + gemini_cli adapters; claude_sdk and
# codex_cli adapter imports + registry entries removed to avoid pulling the
# claude_agent_sdk runtime dependency. Re-sync by reintroducing those imports
# if future experiments require those providers.
"""
Provider Block — 호흡기 (LLM API Communication)

LLM 프로바이더와의 통신을 담당하는 장기.
Adapter 패턴으로 Ollama, OpenAI, Anthropic 등을 통합.

Config를 단일 소스로 사용 — model, temperature 등은 항상 Config에서 읽음.

Reference:
- OC: extensions/ollama/ (NDJSON streaming, model discovery)
- CC: rust/crates/api/client.rs (SSE parser, retry)
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from ludex.core.block import Block
from ludex.core.port import Port
from ludex.blocks.adapters.base import BaseAdapter, AdapterResponse
from ludex.blocks.adapters.ollama import OllamaAdapter
from ludex.blocks.adapters.openai_compat import OpenAIAdapter
from ludex.blocks.adapters.anthropic import AnthropicAdapter
from ludex.blocks.adapters.claude_cli import ClaudeCliAdapter
from ludex.blocks.adapters.gemini_cli import GeminiCliAdapter

logger = logging.getLogger(__name__)


# --- Provider Response Types ---

@dataclass(frozen=True)
class LLMResponse:
    """LLM 응답 결과"""
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    tool_calls: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LLMError:
    """LLM 호출 에러"""
    error_type: str     # "connection", "timeout", "rate_limit", "model_error", "auth"
    message: str
    retryable: bool = True
    retry_after_ms: Optional[float] = None


# --- Adapter Registry ---

ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "ollama": OllamaAdapter,
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "claude_cli": ClaudeCliAdapter,
    "gemini_cli": GeminiCliAdapter,
}

DEFAULT_BASE_URLS: dict[str, str] = {
    "ollama": "http://127.0.0.1:11434",
    "openai": "https://api.openai.com",
    "anthropic": "https://api.anthropic.com",
    "claude_cli": "claude.cmd" if __import__("os").name == "nt" else "claude",
    "gemini_cli": "gemini.cmd" if __import__("os").name == "nt" else "gemini",
}


# --- Provider Block ---

class ProviderBlock(Block):
    """
    LLM 프로바이더 블록. Adapter 패턴으로 다양한 API 지원.

    provides: llm_call, health_check, list_models
    requires: (없음)

    모든 호출 시 Config에서 model, temperature 등을 읽음 (단일 소스 원칙).
    """

    name = "provider"
    provides = [
        Port("llm_call", description="Call LLM with prompt"),
        Port("health_check", description="Check provider health"),
        Port("list_models", description="List available models"),
    ]
    requires = []

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "llama3.1:8b",
        base_url: str = "",
        api_key: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout_ms: int = 30000,
        cwd: str = "",
    ):
        super().__init__()

        # 이 값들은 Config에 주입되며, 이후에는 항상 Config에서 읽음
        self._init_config = {
            "provider": provider,
            "model": model,
            "base_url": base_url or DEFAULT_BASE_URLS.get(provider, "http://127.0.0.1:11434"),
            "api_key": api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout_ms": timeout_ms,
            "cwd": cwd,
        }

        # Adapter 생성
        self._adapter: Optional[BaseAdapter] = None
        self._create_adapter(provider, self._init_config["base_url"], api_key, timeout_ms, cwd)

    def _create_adapter(self, provider: str, base_url: str, api_key: str, timeout_ms: int, cwd: str = ""):
        adapter_cls = ADAPTER_REGISTRY.get(provider)
        if adapter_cls:
            # Pass cwd to adapters that support it (claude_cli, gemini_cli)
            kwargs = {"base_url": base_url, "api_key": api_key, "timeout_ms": timeout_ms}
            if provider in ("claude_cli", "gemini_cli") and cwd:
                kwargs["cwd"] = cwd
            self._adapter = adapter_cls(**kwargs)
        else:
            # 기본: OpenAI-compatible
            self._adapter = OpenAIAdapter(base_url=base_url, api_key=api_key, timeout_ms=timeout_ms)
            logger.warning(f"Unknown provider '{provider}', using OpenAI-compatible adapter")

    def on_attach(self):
        # 초기 설정을 Config에 주입 (defaults layer에 없는 것만)
        for key, value in self._init_config.items():
            if self._config and self._config.get(key) is None:
                self._config.set(key, value, layer="defaults")

        # Config 변경 시 어댑터 재생성
        self._listen("config.changed", self._on_config_changed)

    def _on_config_changed(self, key: str = "", new: Any = None, **kwargs):
        if key == "provider" and new:
            # 프로바이더 자체가 바뀌면 어댑터 재생성
            self._create_adapter(
                new,
                self._cfg("base_url", ""),
                self._cfg("api_key", ""),
                self._cfg("timeout_ms", 30000),
            )
            logger.info(f"Provider adapter switched to: {new}")

    # --- Provides: llm_call ---

    def handle_llm_call(self, prompt: str = "", system: str = "", tools: list | None = None, messages: list[dict] | None = None) -> LLMResponse | LLMError:
        """
        LLM API 호출. 항상 Config에서 현재 model/temperature를 읽음.

        messages가 주어지면 멀티턴 대화 (prompt 무시).
        messages가 없으면 prompt를 단일 user 메시지로 처리.
        """
        if not self._adapter:
            return LLMError(error_type="connection", message="No adapter configured", retryable=False)

        # Config가 단일 소스 (호르몬 신호 수용)
        model = self._cfg("model", "llama3.1:8b")
        temperature = self._cfg("temperature", 0.7)
        max_tokens = self._cfg("max_tokens", 4096)

        with self._timed("llm_call"):
            start = time.perf_counter()
            try:
                result: AdapterResponse = self._adapter.call(
                    model=model,
                    prompt=prompt,
                    system=system,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                )

                elapsed = (time.perf_counter() - start) * 1000

                response = LLMResponse(
                    content=result.content,
                    model=model,
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                    latency_ms=elapsed,
                    tool_calls=result.tool_calls,
                    raw=result.raw,
                )

                # Bus에 응답 발행
                self._publish("llm.response", {
                    "model": model,
                    "tokens_in": response.tokens_in,
                    "tokens_out": response.tokens_out,
                    "latency_ms": response.latency_ms,
                })
                self._emit("llm.responded", model=model)

                return response

            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                error_type = self._classify_error(e)
                self._emit("llm.failed", model=model, error=str(e))
                return LLMError(
                    error_type=error_type,
                    message=str(e),
                    retryable=error_type != "auth",
                )

    # --- Provides: health_check ---

    def handle_health_check(self) -> dict:
        if not self._adapter:
            return {"status": "unhealthy", "error": "No adapter"}
        return self._adapter.health_check()

    # --- Provides: list_models ---

    def handle_list_models(self) -> list[str]:
        if not self._adapter:
            return []
        return self._adapter.list_models()

    # --- Error Classification ---

    @staticmethod
    def _classify_error(error: Exception) -> str:
        """에러를 분류 (OC shouldRetry 패턴)"""
        msg = str(error).lower()
        if "401" in msg or "403" in msg or "auth" in msg or "api_key" in msg:
            return "auth"
        if "429" in msg or "rate" in msg:
            return "rate_limit"
        if "timeout" in msg:
            return "timeout"
        if "500" in msg or "502" in msg or "503" in msg:
            return "model_error"
        return "connection"
