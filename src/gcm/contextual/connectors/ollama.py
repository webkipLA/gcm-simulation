"""Ollama (local models) through its native chat API.

Configuration: ``OLLAMA_URL`` (default ``http://localhost:11434``), ``OLLAMA_MODEL`` and
``OLLAMA_THINK`` (``true``/``false``; unset leaves the decision to Ollama, which lets thinking
models such as qwen3 think). An explicit ``think`` setting becomes part of the connector identity,
so answers with and without thinking never share a cache entry.
Structured output: Ollama accepts a JSON schema in the ``format`` field. ``seed`` and
``temperature`` go into ``options``, so repeated calls with the same seed are reproducible for
the same model file and version.
"""

from __future__ import annotations

import os

import httpx

from gcm.contextual.connectors.base import BaseConnector, ConnectorLimits
from gcm.contextual.connectors.http import post_json

DEFAULT_URL = "http://localhost:11434"


class OllamaConnector(BaseConnector):
    name = "ollama"

    def __init__(
        self,
        model: str | None = None,
        url: str | None = None,
        limits: ConnectorLimits | None = None,
        *,
        think: bool | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        model = model or os.environ.get("OLLAMA_MODEL", "")
        if not model:
            raise ValueError("no model: pass model= or set OLLAMA_MODEL")
        limits = limits or ConnectorLimits(max_concurrency=2, timeout_s=180.0)
        super().__init__(model, limits)
        self.url = (url or os.environ.get("OLLAMA_URL", DEFAULT_URL)).rstrip("/")
        self.think = think
        self._client = httpx.Client(timeout=limits.timeout_s, transport=transport)

    def identity(self) -> dict:
        out = {"connector": self.name, "model": self.model, "url": self.url}
        if self.think is not None:
            out["think"] = self.think
        return out

    def _call(self, system, user, temperature, seed, schema, meta):
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": float(temperature)},
        }
        if seed is not None:
            payload["options"]["seed"] = int(seed)
        if schema is not None:
            payload["format"] = schema
        if self.think is not None:
            payload["think"] = self.think
        data = post_json(self._client, f"{self.url}/api/chat", payload)
        text = (data.get("message") or {}).get("content", "") or ""
        usage = {
            k: data[k]
            for k in ("prompt_eval_count", "eval_count", "total_duration", "eval_duration")
            if k in data
        }
        return text, str(data.get("model", self.model)), usage or None


__all__ = ["DEFAULT_URL", "OllamaConnector"]
