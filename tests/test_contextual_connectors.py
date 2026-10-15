"""Connector interface, answer parsing, Mock connector, cache and log (no network involved)."""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from gcm.contextual.answers import extract_json, interpret
from gcm.contextual.cache import DiskCache, request_key
from gcm.contextual.connectors import (
    BaseConnector,
    Connector,
    ConnectorError,
    ConnectorLimits,
    MockConnector,
    RateLimiter,
    TransientError,
)
from gcm.contextual.paths import load_env
from gcm.contextual.runlog import read_jsonl, write_jsonl
from gcm.contextual.scenario import load_scenarios


# ------------------------------------------------------------------------------- answers
def test_extract_json_tolerates_fences_and_surrounding_text():
    assert extract_json('{"eligible": true}') == {"eligible": True}
    assert extract_json('```json\n{"reason": "x", "eligible": false}\n```') == {
        "reason": "x",
        "eligible": False,
    }
    assert extract_json('Sure. {"eligible": true} Hope that helps.') == {"eligible": True}
    assert extract_json('{broken} then {"eligible": false}') == {"eligible": False}
    assert extract_json("[true]") is None
    assert extract_json("yes") is None and extract_json("") is None


def test_only_boolean_verdicts_are_valid():
    ok = interpret({"reason": "r", "eligible": True}, "pairwise", ("c1",))
    assert ok[0].valid and ok[0].eligible is True and ok[0].reason == "r"
    for bad in ({"eligible": "true"}, {"eligible": 1}, {"answer": True}, None):
        (cell,) = interpret(bad, "pairwise", ("c1",))
        assert not cell.valid and cell.eligible is None and cell.problem


def test_per_row_answers_are_matched_by_opportunity_id():
    parsed = {
        "answers": [
            {"opportunity": "c1", "eligible": True},
            {"opportunity": "[c2]", "eligible": False},
            {"opportunity": "c3", "eligible": True},
            {"opportunity": "c3", "eligible": False},
        ]
    }
    cells = {c.col_id: c for c in interpret(parsed, "per_row", ("c1", "c2", "c3", "c4"))}
    assert cells["c1"].eligible is True and cells["c2"].eligible is False
    assert not cells["c3"].valid and "more than once" in cells["c3"].problem
    assert not cells["c4"].valid and "missing" in cells["c4"].problem
    assert all(not c.valid for c in interpret({"answers": "none"}, "per_row", ("c1",)))


# ------------------------------------------------------------------------------- base connector
class _Scripted(BaseConnector):
    """Raises the scripted exceptions in turn, then answers."""

    name = "scripted"

    def __init__(self, script, limits):
        self.sleeps: list[float] = []
        super().__init__("scripted-model", limits, sleep=self.sleeps.append)
        self.script = list(script)
        self.calls = 0

    def _call(self, system, user, temperature, seed, schema, meta):
        self.calls += 1
        if self.script:
            raise self.script.pop(0)
        return '{"eligible": true}', "scripted-model-v1", {"total_tokens": 7}


def test_transient_failures_are_retried_with_exponential_backoff():
    c = _Scripted([TransientError("timeout"), TransientError("503")], ConnectorLimits())
    assert isinstance(c, Connector)
    out = c.complete("s", "u", temperature=0.2, seed=1)
    assert out.error is None and out.parsed == {"eligible": True}
    assert out.attempts == 3 and c.sleeps == [1.0, 2.0]
    assert out.model_id == "scripted-model-v1" and out.usage == {"total_tokens": 7}
    assert out.latency_s >= 0


def test_exhausted_retries_and_permanent_errors_are_reported_not_raised():
    limits = ConnectorLimits(max_retries=2, backoff_s=0.5, max_backoff_s=0.75)
    c = _Scripted([TransientError("x")] * 5, limits)
    out = c.complete("s", "u")
    assert out.error and "TransientError" in out.error and out.parsed is None
    assert c.calls == 3 and c.sleeps == [0.5, 0.75]  # capped backoff, no sleep after the last
    c = _Scripted([ConnectorError("401 unauthorized")], ConnectorLimits())
    out = c.complete("s", "u")
    assert "401" in out.error and c.calls == 1 and c.sleeps == []


def test_unexpected_exceptions_are_recorded_and_do_not_abort():
    c = _Scripted([KeyError("choices")], ConnectorLimits())
    out = c.complete("s", "u")
    assert out.error.startswith("unexpected KeyError") and c.calls == 1 and out.parsed is None


def test_retry_after_of_the_server_is_respected():
    c = _Scripted([TransientError("429", retry_after_s=7.0)], ConnectorLimits())
    assert c.complete("s", "u").error is None and c.sleeps == [7.0]


def test_rate_limiter_spaces_request_starts():
    now = [100.0]
    waited: list[float] = []

    def sleep(seconds: float) -> None:
        waited.append(seconds)
        now[0] += seconds

    limiter = RateLimiter(120, clock=lambda: now[0], sleep=sleep)  # one request per 0.5 s
    assert [limiter.wait() for _ in range(3)] == [0.0, 0.5, 0.5]
    assert waited == [0.5, 0.5]
    assert RateLimiter(None).wait() == 0.0


# ------------------------------------------------------------------------------- mock
@pytest.fixture(scope="module")
def scenario():
    return load_scenarios()["reference_hierarchical"]


def _ask(mock, row, col, loop=0, seed=0, mode="pairwise"):
    meta = {"row_id": row, "col_ids": [col], "loop": loop, "mode": mode}
    return mock.complete("s", "u", seed=seed, meta=meta)


def test_mock_answers_from_the_target_matrix(scenario):
    mock = MockConnector.for_scenario(scenario)
    assert _ask(mock, "m03", "c07").parsed["eligible"] is True
    assert _ask(mock, "m07", "c03").parsed["eligible"] is False
    inverted = MockConnector.for_scenario(scenario, noise=1.0)
    assert _ask(inverted, "m03", "c07").parsed["eligible"] is False
    out = mock.complete(
        "s", "u", meta={"row_id": "m09", "col_ids": ["c10", "c01"], "mode": "per_row"}
    )
    assert [a["eligible"] for a in out.parsed["answers"]] == [True, False]


def test_mock_noise_is_deterministic_per_request(scenario):
    a = MockConnector.for_scenario(scenario, noise=0.3, seed=5)
    b = MockConnector.for_scenario(scenario, noise=0.3, seed=5)
    answers_a = [_ask(a, "m02", "c05", loop).parsed["eligible"] for loop in range(200)]
    answers_b = [_ask(b, "m02", "c05", loop).parsed["eligible"] for loop in range(200)]
    assert answers_a == answers_b
    assert 0.55 < np.mean(answers_a) < 0.85  # target is True, about 30 % flipped
    other = MockConnector.for_scenario(scenario, noise=0.3, seed=6)
    assert answers_a != [_ask(other, "m02", "c05", loop).parsed["eligible"] for loop in range(200)]


def test_mock_can_return_invalid_answers_and_needs_coordinates(scenario):
    mock = MockConnector.for_scenario(scenario, invalid_rate=1.0)
    out = _ask(mock, "m01", "c01")
    assert out.error is None and out.parsed is None and out.text
    assert "coordinates" in mock.complete("s", "u").error
    identity = MockConnector.for_scenario(scenario, noise=0.1).identity()
    assert identity != MockConnector.for_scenario(scenario, noise=0.2).identity()
    assert identity["target"].startswith("10x10:")


# ------------------------------------------------------------------------------- cache, log, env
def test_cache_key_covers_the_full_request(tmp_path):
    base = {
        "identity": {"connector": "mock", "model": "m"},
        "system": "s",
        "user": "u",
        "temperature": 0.7,
        "seed": 1,
        "schema": {"type": "object"},
        "loop": 0,
    }
    keys = {request_key(**base)}
    for change in (
        {"identity": {"connector": "mock", "model": "other"}},
        {"system": "S"},
        {"user": "U"},
        {"temperature": 0.0},
        {"seed": 2},
        {"schema": None},
        {"loop": 1},
    ):
        keys.add(request_key(**{**base, **change}))
    assert len(keys) == 8
    cache = DiskCache(tmp_path / "cache")
    key = request_key(**base)
    assert cache.get(key) is None and key not in cache and len(cache) == 0
    cache.put(key, {"completion": {"text": "ü"}})
    assert cache.get(key) == {"completion": {"text": "ü"}} and key in cache and len(cache) == 1


def test_jsonl_roundtrip(tmp_path):
    records = [{"b": 2, "a": "ä"}, {"cells": [{"eligible": None}]}]
    path = write_jsonl(tmp_path / "runs" / "x.jsonl", records)
    assert read_jsonl(path) == records
    assert json.loads(path.read_text(encoding="utf-8").splitlines()[0]) == records[0]


def test_env_file_is_read_without_overriding_the_environment(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\nGCM_TEST_URL=http://localhost:11434\nexport GCM_TEST_KEY='secret'\n"
        "GCM_TEST_KEPT=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GCM_TEST_KEPT", "from-environment")
    monkeypatch.delenv("GCM_TEST_URL", raising=False)
    monkeypatch.delenv("GCM_TEST_KEY", raising=False)
    read = load_env(env)
    assert read["GCM_TEST_KEY"] == "secret"
    assert os.environ["GCM_TEST_URL"] == "http://localhost:11434"
    assert os.environ["GCM_TEST_KEPT"] == "from-environment"
    assert load_env(tmp_path / "missing.env") == {}
    monkeypatch.delenv("GCM_TEST_URL")
    monkeypatch.delenv("GCM_TEST_KEY")
