"""Google Gemini through the REST API (``generateContent``), without an SDK.

Configuration: ``GEMINI_API_KEY`` and ``GEMINI_MODEL`` (e.g. ``gemini-2.5-flash``).
Structured output: ``responseMimeType: application/json`` with ``responseSchema``. Gemini does
not accept ``additionalProperties`` in schemas, so it is stripped. Gemini has a ``seed``
generation parameter; it is passed on, but the API does not promise determinism.
"""

from __future__ import annotations

import os

import httpx

from gcm.contextual.connectors.base import BaseConnector, ConnectorError, ConnectorLimits
from gcm.contextual.connectors.http import post_json, strip_unsupported

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiConnector(BaseConnector):
    name = "gemini"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        limits: ConnectorLimits | None = None,
        *,
        base_url: str | None = None,
        thinking_budget: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        model = model or os.environ.get("GEMINI_MODEL", "")
        api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        if not model or not api_key:
            raise ValueError("set GEMINI_API_KEY and GEMINI_MODEL (or pass them)")
        limits = limits or ConnectorLimits(
            max_concurrency=2, timeout_s=120.0, requests_per_minute=12.0
        )
        super().__init__(model, limits)
        self.api_key = api_key
        self.base_url = (base_url or os.environ.get("GEMINI_BASE_URL", DEFAULT_BASE_URL)).rstrip(
            "/"
        )
        self.thinking_budget = thinking_budget
        self._client = httpx.Client(timeout=limits.timeout_s, transport=transport)

    def identity(self) -> dict:
        return {
            "connector": self.name,
            "model": self.model,
            "thinking_budget": self.thinking_budget,
        }

    def _call(self, system, user, temperature, seed, schema, meta):
        config: dict = {"temperature": float(temperature)}
        if seed is not None:
            config["seed"] = int(seed)
        if schema is not None:
            config["responseMimeType"] = "application/json"
            config["responseSchema"] = strip_unsupported(schema)
        if self.thinking_budget is not None:
            config["thinkingConfig"] = {"thinkingBudget": int(self.thinking_budget)}
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": config,
        }
        url = f"{self.base_url}/models/{self.model}:generateContent"
        data = post_json(
            self._client,
            url,
            payload,
            {"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
        )
        candidates = data.get("candidates") or []
        if not candidates:
            raise ConnectorError(f"no candidates in response: {str(data)[:200]}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        return text, str(data.get("modelVersion", self.model)), data.get("usageMetadata")


__all__ = ["DEFAULT_BASE_URL", "GeminiConnector"]
