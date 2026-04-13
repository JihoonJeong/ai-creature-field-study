"""Capture LLM CLI version + resolved model identifiers at experiment start.

The provider:model strings passed to experiment scripts (e.g. claude_cli:haiku)
may be aliases that the CLI resolves to specific snapshots. Snapshots drift
over time, so summaries should record what was actually in use at run time.

Records, per unique brain spec:
- requested: the spec passed by the experiment script
- cli_version: output of the CLI's --version flag
- resolved_id: the snapshot identifier the CLI is currently bound to

For gemini_cli we pass a pinned version string and skip self-report — the
model's own self-identification via prompt is unreliable.
"""
from __future__ import annotations

import subprocess


_RESOLVE_PROMPT = (
    "Reply with EXACTLY your model identifier string "
    "(e.g. claude-haiku-4-5-20251001) and nothing else."
)


def _run(cmd: list[str], timeout: int = 60) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (result.stdout or result.stderr).strip()
        return out or "<empty>"
    except Exception as e:
        return f"<error: {e}>"


def record_brain_versions(brain_specs: list[str]) -> dict:
    seen: dict[str, dict] = {}
    for spec in brain_specs:
        if spec in seen:
            continue
        provider, model = spec.split(":", 1)
        info = {"requested": spec}
        if provider == "claude_cli":
            info["cli_version"] = _run(["claude", "--version"])
            info["resolved_id"] = _run(["claude", "--model", model, "-p", _RESOLVE_PROMPT])
        elif provider == "gemini_cli":
            info["cli_version"] = _run(["gemini", "--version"])
            info["resolved_id"] = model  # pinned; self-report unreliable
        else:
            info["cli_version"] = "<unknown provider>"
            info["resolved_id"] = "<unknown provider>"
        seen[spec] = info
    return seen
