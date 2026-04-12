"""
Resilience Block — 면역계 보조 (재시도, 폴백, 서킷 브레이커)

Provider를 감싸서 안정성을 제공하는 장기.
"Engine → Resilience.llm_call() → Provider.llm_call()" 래핑 체인.

Reference:
- OC: src/infra/backoff.ts computeBackoff(), src/infra/retry.ts retryAsync()
- OC: gateway/channel-health-monitor.ts (circuit breaker, restart policy)
- CC: query_engine.py (budget/turn limit as safety)
"""

from __future__ import annotations

import time
import random
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ludex.core.block import Block
from ludex.core.port import Port
from ludex.blocks.provider import LLMResponse, LLMError

logger = logging.getLogger(__name__)


@dataclass
class RetryInfo:
    """재시도 정보 (모니터링/로깅용)"""
    attempt: int
    max_attempts: int
    delay_ms: float
    error_type: str
    error_message: str


class ResilienceBlock(Block):
    """
    안정성 블록. Provider를 감싸서 재시도, 백오프, 서킷 브레이커 적용.

    provides: llm_call (래핑된 버전)
    requires: llm_call (원본 Provider)

    래핑 체인: Engine → Resilience → Provider
    """

    name = "resilience"
    provides = [
        Port("llm_call", description="Resilient LLM call (wraps provider)"),
        Port("reset_circuit_breaker", description="Force-reset circuit breaker (immune override)"),
    ]
    requires = [
        Port("llm_call", description="Raw LLM call from Provider", required=True),
    ]

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_ms: float = 300,
        max_delay_ms: float = 30000,
        backoff_factor: float = 2.0,
        jitter: float = 0.1,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_reset_ms: float = 60000,
        fallback_models: list[str] | None = None,
    ):
        super().__init__()
        # Retry config (OC retryAsync defaults)
        self.max_retries = max_retries
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_factor = backoff_factor
        self.jitter = jitter

        # Circuit breaker (OC channel-health-monitor pattern)
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_reset_ms = circuit_breaker_reset_ms
        self._consecutive_failures: int = 0
        self._circuit_open: bool = False
        self._circuit_opened_at: float = 0.0

        # Fallback models
        self.fallback_models = fallback_models or []
        self._current_fallback_index: int = 0

        # Stats
        self._total_retries: int = 0
        self._total_failures: int = 0
        self._total_successes: int = 0

    def on_attach(self):
        self._listen("config.changed", self._on_config_changed)

    def _on_config_changed(self, key: str = "", **kwargs):
        if key == "fallback_models":
            self.fallback_models = kwargs.get("new", [])

    # --- Provides: llm_call (resilient wrapper) ---

    def handle_llm_call(self, prompt: str = "", system: str = "", tools: list | None = None, messages: list[dict] | None = None) -> LLMResponse | LLMError:
        """
        래핑된 LLM 호출. 내부적으로 Provider의 llm_call을 호출하되:
        1. 서킷 브레이커 체크
        2. 재시도 + 지수 백오프
        3. 에러 유형별 복구 전략
        4. 폴백 모델 전환
        """
        # 서킷 브레이커 체크
        if self._circuit_open:
            if self._should_reset_circuit():
                self._close_circuit()
            else:
                return LLMError(
                    error_type="circuit_breaker",
                    message=f"Circuit breaker open ({self._consecutive_failures} consecutive failures)",
                    retryable=False,
                )

        # 재시도 루프
        last_error: Optional[LLMError] = None

        for attempt in range(1, self.max_retries + 1):
            self._emit("llm.calling", attempt=attempt, model=self._cfg("model"))

            result = self.call_port("llm_call", prompt=prompt, system=system, tools=tools, messages=messages)

            if isinstance(result, LLMResponse):
                # 성공
                self._on_success()
                return result

            # 실패
            last_error = result
            self._on_failure(result)

            # 재시도 불가능한 에러
            if not result.retryable:
                logger.warning(f"Non-retryable error: {result.error_type} — {result.message}")
                break

            # 마지막 시도였으면 break
            if attempt >= self.max_retries:
                break

            # 재시도 대기 (OC computeBackoff 패턴)
            delay = self._compute_backoff(attempt, result)
            retry_info = RetryInfo(
                attempt=attempt,
                max_attempts=self.max_retries,
                delay_ms=delay,
                error_type=result.error_type,
                error_message=result.message,
            )
            self._publish("retry.attempted", {
                "attempt": attempt,
                "delay_ms": delay,
                "error_type": result.error_type,
            })
            logger.info(f"Retry {attempt}/{self.max_retries} after {delay:.0f}ms — {result.error_type}")

            time.sleep(delay / 1000)

            # Rate limit이면 더 긴 대기
            if result.error_type == "rate_limit" and result.retry_after_ms:
                time.sleep(result.retry_after_ms / 1000)

        # 모든 재시도 실패 — 폴백 모델 시도
        if self.fallback_models and last_error:
            fallback_result = self._try_fallback(prompt, system, tools, messages)
            if fallback_result:
                return fallback_result

        return last_error or LLMError(
            error_type="exhausted",
            message="All retry attempts exhausted",
            retryable=False,
        )

    # --- Backoff (OC computeBackoff pattern) ---

    def _compute_backoff(self, attempt: int, error: LLMError) -> float:
        """
        지수 백오프 + jitter 계산.
        OC 공식: base * factor^(attempt-1), clamped to maxMs, + jitter
        """
        # Rate limit이면 retry_after 우선
        if error.error_type == "rate_limit" and error.retry_after_ms:
            return max(error.retry_after_ms, self.initial_delay_ms)

        base = self.initial_delay_ms * (self.backoff_factor ** (attempt - 1))
        jitter_amount = base * self.jitter * random.random()
        delay = min(base + jitter_amount, self.max_delay_ms)
        return max(delay, self.initial_delay_ms)

    # --- Circuit Breaker ---

    def _on_success(self):
        self._consecutive_failures = 0
        self._total_successes += 1
        if self._circuit_open:
            self._close_circuit()
        # Vital signs 업데이트
        if self._config:
            self._config.set("_consecutive_failures", 0, layer="session")
            self._config.set("_circuit_breaker_open", False, layer="session")

    def _on_failure(self, error: LLMError):
        self._consecutive_failures += 1
        self._total_failures += 1
        if self._consecutive_failures >= self.circuit_breaker_threshold:
            self._open_circuit()
        # Vital signs 업데이트
        if self._config:
            self._config.set("_consecutive_failures", self._consecutive_failures, layer="session")

    def _open_circuit(self):
        if not self._circuit_open:
            self._circuit_open = True
            self._circuit_opened_at = time.time()
            self._emit("circuit_breaker.opened", failures=self._consecutive_failures)
            logger.warning(f"Circuit breaker OPENED after {self._consecutive_failures} failures")
            if self._config:
                self._config.set("_circuit_breaker_open", True, layer="session")

    def _close_circuit(self):
        if self._circuit_open:
            self._circuit_open = False
            self._consecutive_failures = 0
            self._emit("circuit_breaker.closed")
            logger.info("Circuit breaker CLOSED — system recovered")
            if self._config:
                self._config.set("_circuit_breaker_open", False, layer="session")

    def _should_reset_circuit(self) -> bool:
        elapsed = (time.time() - self._circuit_opened_at) * 1000
        return elapsed >= self.circuit_breaker_reset_ms

    # --- Fallback Models ---

    def _try_fallback(self, prompt: str, system: str, tools: list | None, messages: list[dict] | None = None) -> Optional[LLMResponse]:
        """폴백 모델로 전환 시도"""
        for fallback_model in self.fallback_models:
            if self._config:
                old_model = self._config.get("model")
                self._config.set("model", fallback_model)
                logger.info(f"Trying fallback model: {fallback_model}")

                result = self.call_port("llm_call", prompt=prompt, system=system, tools=tools, messages=messages)

                if isinstance(result, LLMResponse):
                    self._emit("model.fallback_succeeded", old_model=old_model, new_model=fallback_model)
                    return result

                # 실패하면 원래 모델로 복원
                self._config.set("model", old_model)

        return None

    # --- Immune Integration ---

    def handle_reset_circuit_breaker(self) -> dict:
        """면역계에서 서킷 브레이커를 강제 리셋. 모델 교체 후 재시도 허용."""
        was_open = self._circuit_open
        self._close_circuit()
        self._consecutive_failures = 0
        logger.info("Circuit breaker force-reset by immune system")
        return {"was_open": was_open, "now_open": False}

    # --- Stats ---

    def get_stats(self) -> dict:
        return {
            "total_retries": self._total_retries,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "consecutive_failures": self._consecutive_failures,
            "circuit_breaker_open": self._circuit_open,
        }
