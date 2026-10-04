"""The experiment: factors, call planning and the runner.

One experiment configuration fixes a scenario and one level of every factor. The runner asks the
eligibility question ``loops`` times for every (row, opportunity) pair and returns one record per
call. Default is one call per pair and loop; the ``per_row`` mode asks about all opportunities
of one row in a single call.

Factors, following the robustness audit of the Exposé (TRAILS, Ye et al. 2026):

===================  =========================================================================
representation       prose, role list or statute (representational format)
wording              two paraphrases of the instruction (linguistic framing)
perspective          neutral observer or first-person persona (agent specification)
item_order           canonical or shuffled anew in every loop (instruction order)
language             English or German
model                the connector the configuration is run with (model substrate)
seed, temperature    inference settings
===================  =========================================================================

Nothing in this module runs on import. Calls are issued by :func:`run_experiment` only, and with
``cache_only=True`` not even there: then the function reports what the cache already holds.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

from gcm.contextual import prompts
from gcm.contextual.answers import interpret
from gcm.contextual.cache import DiskCache, request_key
from gcm.contextual.connectors.base import Completion, Connector
from gcm.contextual.representation import (
    ITEM_ORDERS,
    REPRESENTATIONS,
    entity_sentence,
    item_order,
    render,
)
from gcm.contextual.runlog import write_jsonl
from gcm.contextual.scenario import Scenario

FACTORS = ("representation", "wording", "perspective", "item_order", "language")


@dataclass(frozen=True)
class ExperimentConfig:
    """One level of every factor for one scenario."""

    scenario_id: str
    representation: str = "prose"
    wording: str = "a"
    perspective: str = "observer"
    item_order: str = "canonical"
    language: str = "en"
    mode: str = "pairwise"
    with_reason: bool = True
    show_importance: bool = False
    loops: int = 5
    temperature: float = 0.7
    seed: int = 0

    def __post_init__(self) -> None:
        checks = (
            ("representation", REPRESENTATIONS),
            ("wording", prompts.WORDINGS),
            ("perspective", prompts.PERSPECTIVES),
            ("item_order", ITEM_ORDERS),
            ("mode", prompts.MODES),
        )
        for name, allowed in checks:
            if getattr(self, name) not in allowed:
                raise ValueError(f"{name} must be one of {allowed}, got {getattr(self, name)!r}")
        if self.loops < 1:
            raise ValueError("loops must be at least 1")
        if self.temperature < 0:
            raise ValueError("temperature must not be negative")

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def config_hash(self) -> str:
        blob = json.dumps(self.as_dict(), sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]

    def label(self, vary: tuple[str, ...] = FACTORS) -> str:
        """Short name built from the given factors, e.g. ``prose|a|observer|canonical|en``."""
        return "|".join(str(getattr(self, name)) for name in vary)


def expand_grid(base: ExperimentConfig, **levels) -> list[ExperimentConfig]:
    """All combinations of the given factor levels, e.g. ``representation=[...], wording=[...]``."""
    names = list(levels)
    return [
        replace(base, **dict(zip(names, combo, strict=True)))
        for combo in itertools.product(*(levels[n] for n in names))
    ]


@dataclass(frozen=True)
class Request:
    """One planned call."""

    config: ExperimentConfig
    row_id: str
    col_ids: tuple[str, ...]
    loop: int
    call_seed: int
    system: str
    user: str
    schema: dict = field(compare=False, hash=False)
    template_hash: str = ""

    @property
    def meta(self) -> dict:
        return {
            "row_id": self.row_id,
            "col_ids": list(self.col_ids),
            "loop": self.loop,
            "mode": self.config.mode,
        }


def call_seed(seed: int, loop: int, row_id: str, col_ids: tuple[str, ...]) -> int:
    """A reproducible seed per call. It differs between loops, so that a provider that honours
    seeds returns independent samples instead of the same answer ``loops`` times."""
    blob = f"{seed}|{loop}|{row_id}|{','.join(col_ids)}".encode()
    return int(hashlib.sha256(blob).hexdigest()[:8], 16) % 2**31


def n_calls(scenario: Scenario, config: ExperimentConfig) -> int:
    """Number of calls one configuration needs with one connector."""
    n_rows, n_cols = scenario.shape
    return config.loops * n_rows * (n_cols if config.mode == "pairwise" else 1)


def plan_calls(scenario: Scenario, config: ExperimentConfig) -> list[Request]:
    """Every call of one configuration, with fully rendered messages."""
    if config.scenario_id != scenario.id:
        raise ValueError(f"configuration is for {config.scenario_id}, not for {scenario.id}")
    template = prompts.get_template(
        language=config.language,
        row_entity=scenario.row_entity,
        perspective=config.perspective,
        wording=config.wording,
        mode=config.mode,
        with_reason=config.with_reason,
    )
    lang = config.language
    requests: list[Request] = []
    for loop in range(config.loops):
        order = item_order(scenario, config.item_order, seed=f"{config.seed}-{loop}")
        description = render(
            scenario,
            config.representation,
            lang,
            show_importance=config.show_importance,
            order=order,
        )
        listing = "\n".join(
            f"- [{scenario.opportunities[c].id}] {scenario.opportunities[c].label[lang]}"
            for c in order.cols
        )
        for row in scenario.rows:
            common = {
                "organization_description": description,
                "participant": row.label[lang],
                "participant_description": entity_sentence(row, lang),
            }
            if config.mode == "per_row":
                targets = [(tuple(scenario.opportunities[c].id for c in order.cols), listing, "")]
            else:
                targets = [((o.id,), "", o.label[lang]) for o in scenario.opportunities]
            for col_ids, opportunity_list, opportunity in targets:
                system, user = prompts.build_prompt(
                    template,
                    opportunity=opportunity,
                    opportunity_list=opportunity_list,
                    **common,
                )
                requests.append(
                    Request(
                        config=config,
                        row_id=row.id,
                        col_ids=col_ids,
                        loop=loop,
                        call_seed=call_seed(config.seed, loop, row.id, col_ids),
                        system=system,
                        user=user,
                        schema=template.schema,
                        template_hash=template.template_hash,
                    )
                )
    return requests


# -------------------------------------------------------------------------------------- runner
@dataclass
class RunResult:
    """Records of one configuration run with one connector."""

    scenario_id: str
    config: ExperimentConfig
    identity: dict
    records: list[dict]
    n_planned: int
    n_cached: int = 0
    n_new: int = 0
    n_missing: int = 0  # planned but neither cached nor run (cache_only)
    log_path: Path | None = None

    @property
    def complete(self) -> bool:
        return self.n_missing == 0

    @property
    def n_errors(self) -> int:
        return sum(1 for r in self.records if r["error"])

    @property
    def template_hash(self) -> str:
        return self.records[0]["template_hash"] if self.records else ""

    @property
    def model_ids(self) -> list[str]:
        return sorted({r["model_id"] for r in self.records if r["model_id"]})


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", text).strip("-") or "x"


def log_name(scenario_id: str, identity: dict, config: ExperimentConfig) -> str:
    id_hash = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:8]
    connector = _slug(f"{identity.get('connector', '')}-{identity.get('model', '')}")
    return f"{scenario_id}__{connector}-{id_hash}__{config.config_hash}.jsonl"


def _record(request: Request, identity: dict, key: str, stored: dict, cached: bool) -> dict:
    completion = Completion.from_dict(stored["completion"])
    cells = interpret(completion.parsed, request.config.mode, request.col_ids)
    config = request.config
    return {
        "timestamp": stored["timestamp"],
        "request_key": key,
        "cached": cached,
        "connector": identity.get("connector"),
        "model": identity.get("model"),
        "model_id": completion.model_id,
        "identity": identity,
        "template_hash": request.template_hash,
        "scenario": config.scenario_id,
        "representation": config.representation,
        "factors": config.as_dict(),
        "seed": config.seed,
        "call_seed": request.call_seed,
        "temperature": config.temperature,
        "loop": request.loop,
        "row_id": request.row_id,
        "col_ids": list(request.col_ids),
        "system": request.system,
        "user": request.user,
        "text": completion.text,
        "parsed": completion.parsed,
        "cells": [
            {"col_id": c.col_id, "eligible": c.eligible, "reason": c.reason, "problem": c.problem}
            for c in cells
        ],
        "error": completion.error,
        "latency_s": completion.latency_s,
        "usage": completion.usage,
        "attempts": completion.attempts,
    }


def run_experiment(
    scenario: Scenario,
    config: ExperimentConfig,
    connector: Connector,
    *,
    cache: DiskCache | None = None,
    log_dir: str | Path | None = None,
    cache_only: bool = False,
    progress: Callable[[int, int], None] | None = None,
) -> RunResult:
    """Run one configuration with one connector.

    Answers already in ``cache`` are reused; only the remaining calls are issued, in parallel up
    to the connector's concurrency limit. With ``cache_only=True`` no call is issued at all and
    ``n_missing`` tells how many would be needed. When all calls are answered and ``log_dir`` is
    given, the records are written as one JSONL file.
    """
    requests = plan_calls(scenario, config)
    identity = connector.identity()
    keys = [
        request_key(identity, r.system, r.user, config.temperature, r.call_seed, r.schema, r.loop)
        for r in requests
    ]
    records: list[dict | None] = [None] * len(requests)
    todo: list[int] = []
    result = RunResult(scenario.id, config, identity, [], n_planned=len(requests))
    for i, (request, key) in enumerate(zip(requests, keys, strict=True)):
        stored = cache.get(key) if cache is not None else None
        if stored is not None:
            records[i] = _record(request, identity, key, stored, cached=True)
            result.n_cached += 1
        else:
            todo.append(i)
    done = result.n_cached
    if progress:
        progress(done, len(requests))

    def issue(i: int) -> tuple[int, dict]:
        request = requests[i]
        completion = connector.complete(
            request.system,
            request.user,
            temperature=config.temperature,
            seed=request.call_seed,
            schema=request.schema,
            meta=request.meta,
        )
        stored = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completion": completion.as_dict(),
        }
        if cache is not None and completion.error is None:
            cache.put(keys[i], stored)
        return i, stored

    if cache_only:
        result.n_missing = len(todo)
    elif todo:
        workers = max(1, min(connector.limits.max_concurrency, len(todo)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i, stored in pool.map(issue, todo):
                records[i] = _record(requests[i], identity, keys[i], stored, cached=False)
                result.n_new += 1
                done += 1
                if progress:
                    progress(done, len(requests))
    result.records = [r for r in records if r is not None]
    if log_dir is not None and result.complete:
        path = Path(log_dir) / log_name(scenario.id, identity, config)
        result.log_path = write_jsonl(path, result.records)
    return result


__all__ = [
    "FACTORS",
    "ExperimentConfig",
    "Request",
    "RunResult",
    "call_seed",
    "expand_grid",
    "log_name",
    "n_calls",
    "plan_calls",
    "run_experiment",
]
