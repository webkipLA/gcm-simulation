"""Connectors to language models: one interface, several providers."""

from gcm.contextual.connectors.base import (
    BaseConnector,
    Completion,
    Connector,
    ConnectorError,
    ConnectorLimits,
    RateLimiter,
    TransientError,
)
from gcm.contextual.connectors.gemini import GeminiConnector
from gcm.contextual.connectors.mock import MockConnector
from gcm.contextual.connectors.ollama import OllamaConnector
from gcm.contextual.connectors.openai_compat import OpenAICompatibleConnector
from gcm.contextual.connectors.registry import available_connectors

__all__ = [
    "BaseConnector",
    "Completion",
    "Connector",
    "ConnectorError",
    "ConnectorLimits",
    "GeminiConnector",
    "MockConnector",
    "OllamaConnector",
    "OpenAICompatibleConnector",
    "RateLimiter",
    "TransientError",
    "available_connectors",
]
