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
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_THINKING_LEVEL", "GEMINI_THINKING_BUDGET", "GEMINI_RPM"),
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


FROM_ENV = "from the environment"  # default of the overrides of available_connectors
GEMINI_THINKING_LEVELS = ("minimal", "low", "medium", "high")


def available_connectors(
    read_env: bool = True,
    *,
    gemini_thinking_level: str | None = FROM_ENV,
    ollama_think: bool | None | str = FROM_ENV,
) -> dict[str, Callable[[], Connector]]:
    """Factories for every connector the environment configures, keyed ``<connector>/<model>``.

    ``OLLAMA_MODEL``, ``UNI_API_MODEL`` and ``GEMINI_MODEL`` may list several models separated by
    commas. Factories are returned instead of instances so that the notebook can show the list
    without opening any connection.

    The thinking settings come from the environment unless they are passed here. A passed
    ``gemini_thinking_level`` replaces both ``GEMINI_THINKING_LEVEL`` and
    ``GEMINI_THINKING_BUDGET`` (``None`` = send no thinking setting, the model decides); a passed
    ``ollama_think`` replaces ``OLLAMA_THINK`` (``None`` = Ollama decides).
    """
    if read_env:
        load_env()
    out: dict[str, Callable[[], Connector]] = {}
    think = _flag("OLLAMA_THINK") if ollama_think == FROM_ENV else ollama_think
    for model in _models("OLLAMA_MODEL"):
        out[f"ollama/{model}"] = lambda m=model: OllamaConnector(model=m, think=think)
    if os.environ.get("UNI_API_BASE_URL"):
        for model in _models("UNI_API_MODEL"):
            out[f"university/{model}"] = lambda m=model: OpenAICompatibleConnector(
                model=m, name="university"
            )
    if os.environ.get("GEMINI_API_KEY"):
        if gemini_thinking_level == FROM_ENV:
            level = os.environ.get("GEMINI_THINKING_LEVEL", "").strip().lower() or None
            budget_raw = os.environ.get("GEMINI_THINKING_BUDGET", "").strip()
            budget = int(budget_raw) if budget_raw else None
        else:
            level, budget = gemini_thinking_level, None
        for model in _models("GEMINI_MODEL"):
            out[f"gemini/{model}"] = lambda m=model: GeminiConnector(
                model=m, thinking_level=level, thinking_budget=budget
            )
    return out


__all__ = ["ENV_VARIABLES", "FROM_ENV", "GEMINI_THINKING_LEVELS", "available_connectors"]
