"""Shared HTTP plumbing for the real connectors (httpx, one client per connector)."""

from __future__ import annotations

import httpx

from gcm.contextual.connectors.base import ConnectorError, TransientError

RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def post_json(client: httpx.Client, url: str, payload: dict, headers: dict | None = None) -> dict:
    """POST JSON and return the JSON body; map failures to the connector exceptions."""
    try:
        response = client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise TransientError(f"timeout: {exc}") from exc
    except httpx.HTTPError as exc:
        raise TransientError(f"connection error: {exc}") from exc
    if response.status_code in RETRY_STATUS:
        retry_after = response.headers.get("retry-after")
        raise TransientError(
            f"HTTP {response.status_code}: {response.text[:200]}",
            retry_after_s=float(retry_after) if retry_after and retry_after.isdigit() else None,
        )
    if response.status_code >= 400:
        raise ConnectorError(f"HTTP {response.status_code}: {response.text[:300]}")
    try:
        return response.json()
    except ValueError as exc:
        raise TransientError(f"response is not JSON: {response.text[:200]}") from exc


def strip_unsupported(schema: dict, keys: tuple[str, ...] = ("additionalProperties",)) -> dict:
    """A copy of ``schema`` without the given keys (some providers reject them)."""
    if isinstance(schema, dict):
        return {k: strip_unsupported(v, keys) for k, v in schema.items() if k not in keys}
    if isinstance(schema, list):
        return [strip_unsupported(v, keys) for v in schema]
    return schema


__all__ = ["RETRY_STATUS", "post_json", "strip_unsupported"]
