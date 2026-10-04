"""One small interface to every language model.

``complete(system, user, temperature, seed, schema)`` returns the raw text, the parsed JSON
answer, the model id reported by the provider, the latency and the token usage where available.
The optional ``meta`` argument carries the coordinates of the request (row, opportunities, loop).
Real connectors ignore it; the Mock connector needs it to look up its target matrix.

A connector never raises for a failed request: after the retries are exhausted it returns a
:class:`Completion` with ``error`` set, and the runner counts it. Retries use exponential backoff;
every connector has its own timeout, concurrency limit and rate limit.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from gcm.contextual.answers import extract_json


@dataclass(frozen=True)
class ConnectorLimits:
    timeout_s: float = 60.0
    max_retries: int = 4  # retries after the first attempt
    backoff_s: float = 1.0  # wait before the first retry; doubles with every further retry
    max_backoff_s: float = 30.0
    max_concurrency: int = 4  # parallel requests the runner may issue
    requests_per_minute: float | None = None  # None = no rate limit


@dataclass
class Completion:
    text: str
    parsed: dict | None
    model_id: str
    latency_s: float
    usage: dict | None = None
    error: str | None = None
    attempts: int = 1

    def as_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict) -> Completion:
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__})


@runtime_checkable
class Connector(Protocol):
    name: str
    model: str
    limits: ConnectorLimits

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        seed: int | None = None,
        schema: dict | None = None,
        meta: dict | None = None,
    ) -> Completion: ...

    def identity(self) -> dict:
        """What distinguishes this connector's answers: part of the cache key and of the log."""
        ...


class TransientError(Exception):
    """A failure worth retrying (timeout, rate limit, server error)."""

    def __init__(self, message: str, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class ConnectorError(Exception):
    """A failure that a retry will not fix (bad request, missing key, unknown model)."""


class RateLimiter:
    """Spaces request starts so that at most ``requests_per_minute`` are issued."""

    def __init__(
        self,
        requests_per_minute: float | None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.interval = 60.0 / requests_per_minute if requests_per_minute else 0.0
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> float:
        """Block until the next slot; returns the time waited."""
        if not self.interval:
            return 0.0
        with self._lock:
            now = self._clock()
            start = max(now, self._next)
            self._next = start + self.interval
        if start > now:
            self._sleep(start - now)
        return start - now


class BaseConnector:
    """Rate limiting, retries with backoff and timing around one provider call.

    Subclasses implement :meth:`_call`, which returns ``(text, model_id, usage)`` or raises
    :class:`TransientError` / :class:`ConnectorError`.
    """

    name = "base"

    def __init__(
        self,
        model: str,
        limits: ConnectorLimits | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model
        self.limits = limits or ConnectorLimits()
        self._sleep = sleep
        self._rate = RateLimiter(self.limits.requests_per_minute, sleep=sleep)

    def identity(self) -> dict:
        return {"connector": self.name, "model": self.model}

    def _call(
        self,
        system: str,
        user: str,
        temperature: float,
        seed: int | None,
        schema: dict | None,
        meta: dict | None,
    ) -> tuple[str, str, dict | None]:
        raise NotImplementedError

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        seed: int | None = None,
        schema: dict | None = None,
        meta: dict | None = None,
    ) -> Completion:
        started = time.perf_counter()
        attempts = 0
        error = "no attempt made"
        while attempts <= self.limits.max_retries:
            attempts += 1
            self._rate.wait()
            try:
                text, model_id, usage = self._call(system, user, temperature, seed, schema, meta)
            except TransientError as exc:
                error = f"{type(exc).__name__}: {exc}"
                if attempts > self.limits.max_retries:
                    break
                wait = min(self.limits.backoff_s * 2 ** (attempts - 1), self.limits.max_backoff_s)
                if exc.retry_after_s is not None:
                    wait = min(max(wait, exc.retry_after_s), self.limits.max_backoff_s)
                self._sleep(wait)
                continue
            except ConnectorError as exc:
                error = f"{type(exc).__name__}: {exc}"
                break
            return Completion(
                text=text,
                parsed=extract_json(text),
                model_id=model_id,
                latency_s=time.perf_counter() - started,
                usage=usage,
                attempts=attempts,
            )
        return Completion(
            text="",
            parsed=None,
            model_id=self.model,
            latency_s=time.perf_counter() - started,
            error=error,
            attempts=attempts,
        )


__all__ = [
    "BaseConnector",
    "Completion",
    "Connector",
    "ConnectorError",
    "ConnectorLimits",
    "RateLimiter",
    "TransientError",
]
