"""Which connectors are configured, from the environment (and a git-ignored ``.env``)."""

from __future__ import annotations

import os
from collections.abc import Callable

from gcm.contextual.connectors.base import Connector
from gcm.contextual.connectors.gemini import GeminiConnector
from gcm.contextual.connectors.ollama import OllamaConnector
from gcm.contextual.connectors.openai_compat import OpenAICompatibleConnector
from gcm.contextual.paths import load_env

ENV_VARIABLES = {
    "ollama": ("OLLAMA_URL", "OLLAMA_MODEL", "OLLAMA_THINK"),
    "university": ("UNI_API_BASE_URL", "UNI_API_KEY", "UNI_API_MODEL"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL"),
}


def _models(variable: str) -> list[str]:
    return [m.strip() for m in os.environ.get(variable, "").split(",") if m.strip()]


def _flag(variable: str) -> bool | None:
    value = os.environ.get(variable, "").strip().lower()
    if not value:
        return None
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"{variable} must be true or false, got {value!r}")


def available_connectors(read_env: bool = True) -> dict[str, Callable[[], Connector]]:
    """Factories for every connector the environment configures, keyed ``<connector>/<model>``.

    ``OLLAMA_MODEL``, ``UNI_API_MODEL`` and ``GEMINI_MODEL`` may list several models separated by
    commas. Factories are returned instead of instances so that the notebook can show the list
    without opening any connection.
    """
    if read_env:
        load_env()
    out: dict[str, Callable[[], Connector]] = {}
    think = _flag("OLLAMA_THINK")
    for model in _models("OLLAMA_MODEL"):
        out[f"ollama/{model}"] = lambda m=model: OllamaConnector(model=m, think=think)
    if os.environ.get("UNI_API_BASE_URL"):
        for model in _models("UNI_API_MODEL"):
            out[f"university/{model}"] = lambda m=model: OpenAICompatibleConnector(
                model=m, name="university"
            )
    if os.environ.get("GEMINI_API_KEY"):
        for model in _models("GEMINI_MODEL"):
            out[f"gemini/{model}"] = lambda m=model: GeminiConnector(model=m)
    return out


__all__ = ["ENV_VARIABLES", "available_connectors"]
