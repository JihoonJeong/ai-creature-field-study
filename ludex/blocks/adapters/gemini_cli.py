"""
Gemini CLI Adapter — subprocess-based, mirrors Claude CLI pattern.

Connects to Google's Gemini CLI as the LLM backend.
Uses `gemini -p "prompt"` for non-interactive single-shot calls.
MCP organ server wired via inline config (same pattern as Claude CLI).

Usage requires Gemini CLI installed:
    npm install -g @anthropic-ai/gemini-cli
    (or however Gemini CLI is distributed)

Reference: Claude CLI adapter pattern
"""

from __future__ import annotations

import os
import sys
import time
import json
import subprocess
import logging

from ludex.blocks.adapters.base import BaseAdapter, AdapterResponse

logger = logging.getLogger(__name__)

_GEMINI_CMD = "gemini.cmd" if os.name == "nt" else "gemini"


class GeminiCliAdapter(BaseAdapter):
    """Gemini CLI adapter via subprocess."""

    provider_name = "gemini_cli"

    def __init__(self, base_url: str = "", timeout_ms: int = 120000, cwd: str = "", **kwargs):
        super().__init__(base_url=base_url or _GEMINI_CMD, timeout_ms=timeout_ms, **kwargs)
        self._cmd = base_url or _GEMINI_CMD
        self._cwd = cwd or None

    def call(self, model="", prompt="", system="", messages=None,
             temperature=0.7, max_tokens=4096, tools=None):
        """
        Call Gemini CLI with -p flag (non-interactive/headless mode).

        System prompt: Gemini CLI doesn't have --system-prompt flag like Claude.
        We prepend it to the user message as context. Gemini is generally
        less sensitive to prompt injection than Claude Code.

        MCP: wired via gemini mcp add or inline approach.
        """
        # Extract system prompt + last user message (same pattern as claude_cli)
        system_prompt = system or ""
        last_user_msg = ""
        if messages:
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    if not system_prompt:
                        system_prompt = content
                    else:
                        system_prompt = system_prompt + "\n\n" + content
                elif role == "user":
                    last_user_msg = content
            full_prompt = last_user_msg
        else:
            full_prompt = prompt

        if not full_prompt:
            full_prompt = "(no message)"

        # Gemini doesn't have --system-prompt; append as brief context AFTER the question.
        # Putting system context BEFORE the question causes Gemini to over-follow the
        # identity instructions and ignore the actual question (instruction adherence
        # rejection). Putting it after with explicit "answer the question above" framing
        # helps Gemini prioritize the user's actual request.
        if system_prompt:
            # Truncate system prompt to essentials for Gemini
            # (it doesn't need the full creature identity every turn)
            brief_system = system_prompt[:500] if len(system_prompt) > 500 else system_prompt
            full_prompt = (
                f"{full_prompt}\n\n"
                f"(Context about you: {brief_system}. "
                f"Answer the question above first, then stay in character.)"
            )

        # Build command
        cmd = [self._cmd, "-p", full_prompt, "-o", "text", "--approval-mode", "yolo"]
        if self._cwd:
            cmd.extend(["--include-directories", self._cwd])
        if model and model not in ("gemini", "", None):
            cmd.extend(["-m", model])

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_ms / 1000,
                encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                cwd=self._cwd,
            )

            elapsed_ms = (time.time() - start) * 1000
            content = result.stdout.strip()

            if result.returncode != 0 and not content:
                error_msg = result.stderr.strip() or f"CLI exited with code {result.returncode}"
                logger.error(f"Gemini CLI error: {error_msg}")
                return AdapterResponse(
                    content=f"[Error: {error_msg}]",
                    raw={"returncode": result.returncode, "stderr": result.stderr},
                )

            tokens_in = len(full_prompt) // 4
            tokens_out = len(content) // 4

            return AdapterResponse(
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                raw={
                    "returncode": result.returncode,
                    "elapsed_ms": round(elapsed_ms, 1),
                    "cmd": self._cmd,
                },
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.time() - start) * 1000
            return AdapterResponse(
                content="[Error: Gemini CLI timed out]",
                raw={"timeout": True, "elapsed_ms": round(elapsed_ms, 1)},
            )
        except FileNotFoundError:
            return AdapterResponse(
                content=f"[Error: '{self._cmd}' not found. Is Gemini CLI installed?]",
                raw={"error": "command_not_found", "cmd": self._cmd},
            )

    def health_check(self) -> dict:
        try:
            result = subprocess.run(
                [self._cmd, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            version = result.stdout.strip() or result.stderr.strip()
            return {"status": "ok", "version": version, "cmd": self._cmd}
        except FileNotFoundError:
            return {"status": "error", "error": f"'{self._cmd}' not found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_models(self) -> list[str]:
        return ["gemini-2.5-flash", "gemini-2.5-pro"]
