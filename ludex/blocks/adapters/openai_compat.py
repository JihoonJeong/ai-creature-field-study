"""
OpenAI-Compatible Adapter — /v1/chat/completions

Works with: OpenAI, Gemini (OpenAI compat mode), vLLM, LM Studio, etc.
Reference: OC extensions/openai/
"""

from __future__ import annotations

import json
from ludex.blocks.adapters.base import BaseAdapter, AdapterResponse


class OpenAIAdapter(BaseAdapter):
    """OpenAI-compatible API 어댑터"""

    provider_name = "openai"

    def __init__(self, base_url: str = "https://api.openai.com", api_key: str = "", **kwargs):
        super().__init__(base_url=base_url, api_key=api_key, **kwargs)

    def call(self, model, prompt="", system="", messages=None, temperature=0.7, max_tokens=4096, tools=None):
        url = f"{self.base_url}/v1/chat/completions"

        if messages:
            api_messages = list(messages)
        else:
            api_messages = []
            if system:
                api_messages.append({"role": "system", "content": system})
            api_messages.append({"role": "user", "content": prompt})

        body = {
            "model": model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = json.dumps(body).encode("utf-8")
        result = self._request(url, data=data, headers=headers, method="POST")

        choice = result.get("choices", [{}])[0]
        usage = result.get("usage", {})

        return AdapterResponse(
            content=choice.get("message", {}).get("content", ""),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            tool_calls=choice.get("message", {}).get("tool_calls", []),
            raw=result,
        )

    def health_check(self):
        try:
            url = f"{self.base_url}/v1/models"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            result = self._request(url, headers=headers)
            models = [m["id"] for m in result.get("data", [])]
            return {"status": "healthy", "provider": "openai", "models": models}
        except Exception as e:
            return {"status": "unhealthy", "provider": "openai", "error": str(e)}

    def list_models(self):
        health = self.health_check()
        return health.get("models", [])
