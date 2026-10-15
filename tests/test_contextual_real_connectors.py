"""The real connectors against a fake HTTP transport (no network, no keys)."""

from __future__ import annotations

import json

import httpx
import pytest

from gcm.contextual.connectors import (
    ConnectorLimits,
    GeminiConnector,
    OllamaConnector,
    OpenAICompatibleConnector,
    available_connectors,
)
from gcm.contextual.connectors.http import strip_unsupported
from gcm.contextual.prompts import answer_schema

SCHEMA = answer_schema("pairwise", True)


class Fake:
    """Records requests and answers from a script of (status, body) tuples."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            status, body = self.responses.pop(0)
            if isinstance(body, Exception):
                raise body
            return (
                httpx.Response(status, json=body)
                if isinstance(body, dict)
                else httpx.Response(status, text=body)
            )

        return httpx.MockTransport(handler)

    def sent(self, i: int = -1) -> dict:
        return json.loads(self.requests[i].content)


def test_ollama_sends_schema_seed_and_temperature():
    fake = Fake(
        (
            200,
            {
                "model": "qwen3:8b",
                "message": {"role": "assistant", "content": '{"reason": "r", "eligible": true}'},
                "prompt_eval_count": 120,
                "eval_count": 15,
            },
        )
    )
    c = OllamaConnector(model="qwen3:8b", url="http://ollama:11434/", transport=fake.transport())
    out = c.complete("sys", "usr", temperature=0.3, seed=42, schema=SCHEMA)
    assert out.parsed == {"reason": "r", "eligible": True} and out.error is None
    assert out.model_id == "qwen3:8b" and out.usage == {"prompt_eval_count": 120, "eval_count": 15}
    sent = fake.sent()
    assert str(fake.requests[0].url) == "http://ollama:11434/api/chat"
    assert sent["options"] == {"temperature": 0.3, "seed": 42} and sent["format"] == SCHEMA
    assert sent["messages"][0] == {"role": "system", "content": "sys"} and sent["stream"] is False
    assert c.identity() == {
        "connector": "ollama",
        "model": "qwen3:8b",
        "url": "http://ollama:11434",
    }


def test_openai_compatible_uses_bearer_token_and_json_schema():
    fake = Fake(
        (
            200,
            {
                "model": "llama-3.3-70b",
                "choices": [{"message": {"role": "assistant", "content": '{"eligible": false}'}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 5, "total_tokens": 105},
            },
        )
    )
    c = OpenAICompatibleConnector(
        model="llama-3.3-70b",
        base_url="https://api.example.edu/v1/",
        api_key="secret",
        name="university",
        transport=fake.transport(),
    )
    out = c.complete("sys", "usr", temperature=0.0, seed=7, schema=SCHEMA)
    assert out.parsed == {"eligible": False} and out.usage["total_tokens"] == 105
    request = fake.requests[0]
    assert str(request.url) == "https://api.example.edu/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer secret"
    sent = fake.sent()
    assert sent["seed"] == 7 and sent["temperature"] == 0.0
    assert sent["response_format"]["type"] == "json_schema"
    assert sent["response_format"]["json_schema"]["schema"] == SCHEMA
    assert c.identity()["connector"] == "university" and c.identity()["structured"] == "json_schema"


def test_openai_compatible_falls_back_to_json_object_when_schema_is_rejected():
    fake = Fake(
        (400, {"error": {"message": "response_format json_schema is not supported"}}),
        (200, {"choices": [{"message": {"content": '{"eligible": true}'}}]}),
        (200, {"choices": [{"message": {"content": '{"eligible": true}'}}]}),
    )
    c = OpenAICompatibleConnector(
        model="m", base_url="https://h/v1", api_key="", transport=fake.transport()
    )
    assert c.complete("s", "u", schema=SCHEMA).parsed == {"eligible": True}
    assert fake.sent(1)["response_format"] == {"type": "json_object"}
    c.complete("s", "u", schema=SCHEMA)
    assert fake.sent(2)["response_format"] == {"type": "json_object"}  # remembered
    assert c.identity()["structured"] == "json_object"
    assert "authorization" not in fake.requests[0].headers  # no key, no header


def test_transient_http_failures_are_retried_and_permanent_ones_are_not():
    fake = Fake(
        (429, "slow down"),
        (503, "busy"),
        (200, {"choices": [{"message": {"content": '{"eligible": true}'}}]}),
    )
    c = OpenAICompatibleConnector(
        model="m",
        base_url="https://h/v1",
        limits=ConnectorLimits(backoff_s=0.0),
        transport=fake.transport(),
    )
    out = c.complete("s", "u")
    assert out.error is None and out.attempts == 3 and len(fake.requests) == 3
    fake = Fake((401, "unauthorized"))
    c = OpenAICompatibleConnector(model="m", base_url="https://h/v1", transport=fake.transport())
    out = c.complete("s", "u")
    assert "401" in out.error and out.attempts == 1
    fake = Fake((200, httpx.ReadTimeout("slow")), (200, "not json"))
    c = OpenAICompatibleConnector(
        model="m",
        base_url="https://h/v1",
        limits=ConnectorLimits(max_retries=1, backoff_s=0.0),
        transport=fake.transport(),
    )
    out = c.complete("s", "u")
    assert out.error and "not JSON" in out.error and out.attempts == 2


def test_gemini_uses_rest_with_response_schema_and_api_key_header():
    fake = Fake(
        (
            200,
            {
                "candidates": [
                    {"content": {"parts": [{"text": '{"reason": "x", "eligible": true}'}]}}
                ],
                "usageMetadata": {"promptTokenCount": 90, "candidatesTokenCount": 9},
                "modelVersion": "gemini-2.5-flash-001",
            },
        )
    )
    c = GeminiConnector(
        model="gemini-2.5-flash", api_key="k", thinking_budget=0, transport=fake.transport()
    )
    out = c.complete("sys", "usr", temperature=0.5, seed=3, schema=SCHEMA)
    assert out.parsed["eligible"] is True and out.model_id == "gemini-2.5-flash-001"
    assert out.usage["promptTokenCount"] == 90
    request = fake.requests[0]
    assert request.headers["x-goog-api-key"] == "k" and "key=" not in str(request.url)
    assert str(request.url).endswith("/models/gemini-2.5-flash:generateContent")
    sent = fake.sent()
    assert sent["systemInstruction"]["parts"][0]["text"] == "sys"
    cfg = sent["generationConfig"]
    assert cfg["temperature"] == 0.5 and cfg["seed"] == 3
    assert cfg["responseMimeType"] == "application/json"
    assert "additionalProperties" not in json.dumps(cfg["responseSchema"])
    assert cfg["thinkingConfig"] == {"thinkingBudget": 0}
    assert c.identity()["connector"] == "gemini"
    assert c.limits.requests_per_minute == 12.0


def test_strip_unsupported_keeps_the_rest_of_the_schema():
    stripped = strip_unsupported(answer_schema("per_row", True))
    assert "additionalProperties" not in json.dumps(stripped)
    assert stripped["properties"]["answers"]["items"]["required"] == [
        "opportunity",
        "reason",
        "eligible",
    ]


def test_missing_configuration_is_an_error_and_the_registry_reads_the_environment(monkeypatch):
    for var in (
        "OLLAMA_MODEL",
        "UNI_API_BASE_URL",
        "UNI_API_MODEL",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError, match="OLLAMA_MODEL"):
        OllamaConnector()
    with pytest.raises(ValueError, match="UNI_API_BASE_URL"):
        OpenAICompatibleConnector()
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiConnector()
    assert available_connectors(read_env=False) == {}
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b, llama3.1:8b")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("UNI_API_BASE_URL", "https://h/v1")
    monkeypatch.setenv("UNI_API_MODEL", "big-model")
    factories = available_connectors(read_env=False)
    assert list(factories) == [
        "ollama/qwen3:8b",
        "ollama/llama3.1:8b",
        "university/big-model",
        "gemini/gemini-2.5-flash",
    ]
    assert factories["ollama/llama3.1:8b"]().model == "llama3.1:8b"
    assert factories["university/big-model"]().name == "university"
