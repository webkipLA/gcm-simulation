"""Any OpenAI-compatible chat completions API (the university API, OpenWebUI, vLLM, ...).

Configuration: ``UNI_API_BASE_URL`` (e.g. ``https://host/v1``), ``UNI_API_KEY`` (sent as a
Bearer token) and ``UNI_API_MODEL``. Other deployments can be addressed by passing the values
directly or by giving another environment prefix.

Structured output: ``response_format`` with a JSON schema (``json_schema``, the default) where
the server supports it. A server that rejects it makes every call fail with a message that says
to configure ``structured="json_object"`` (or ``UNI_API_STRUCTURED=json_object``) instead. There
is no automatic fallback, because the mode is part of the connector identity and therefore of
the cache key and the logs; switching it in the middle of a run would mix two kinds of answers.
"""

from __future__ import annotations

import os

import httpx

from gcm.contextual.connectors.base import BaseConnector, ConnectorError, ConnectorLimits
from gcm.contextual.connectors.http import post_json


class OpenAICompatibleConnector(BaseConnector):
    name = "openai_compat"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        limits: ConnectorLimits | None = None,
        *,
        env_prefix: str = "UNI_API",
        structured: str | None = None,  # "json_schema" (default) | "json_object" | "none"
        name: str | None = None,
        extra_headers: dict | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        model = model or os.environ.get(f"{env_prefix}_MODEL", "")
        base_url = base_url or os.environ.get(f"{env_prefix}_BASE_URL", "")
        if not model or not base_url:
            raise ValueError(f"set {env_prefix}_BASE_URL and {env_prefix}_MODEL (or pass them)")
        super().__init__(model, limits or ConnectorLimits(max_concurrency=4, timeout_s=120.0))
        if name:
            self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get(f"{env_prefix}_KEY", "")
        structured = structured or os.environ.get(f"{env_prefix}_STRUCTURED", "json_schema")
        if structured not in ("json_schema", "json_object", "none"):
            raise ValueError("structured must be json_schema, json_object or none")
        self.structured = structured
        self._headers = {"Content-Type": "application/json", **(extra_headers or {})}
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"
        self._client = httpx.Client(timeout=self.limits.timeout_s, transport=transport)

    def identity(self) -> dict:
        return {
            "connector": self.name,
            "model": self.model,
            "base_url": self.base_url,
            "structured": self.structured,
        }

    def _payload(self, system, user, temperature, seed, schema) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": float(temperature),
        }
        if seed is not None:
            payload["seed"] = int(seed)
        if schema is not None and self.structured == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "eligibility", "schema": schema, "strict": True},
            }
        elif schema is not None and self.structured == "json_object":
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _call(self, system, user, temperature, seed, schema, meta):
        url = f"{self.base_url}/chat/completions"
        try:
            data = post_json(
                self._client,
                url,
                self._payload(system, user, temperature, seed, schema),
                self._headers,
            )
        except ConnectorError as exc:
            if self.structured == "json_schema" and "response_format" in str(exc):
                raise ConnectorError(
                    f"{exc}; this server rejects json_schema output, configure the connector "
                    "with structured='json_object' (or UNI_API_STRUCTURED=json_object)"
                ) from exc
            raise
        choices = data.get("choices") or []
        if not choices:
            raise ConnectorError(f"no choices in response: {str(data)[:200]}")
        message = choices[0].get("message") or {}
        text = message.get("content") or ""
        if isinstance(text, list):  # some servers return content parts
            text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
        return text, str(data.get("model", self.model)), data.get("usage")


__all__ = ["OpenAICompatibleConnector"]
