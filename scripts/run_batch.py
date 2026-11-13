"""Batch run of the contextual decision structure without the notebook.

Runs a fixed, bounded design in priority order, so that an interrupted night still leaves the
most important configurations complete:

  core        3 reference scenarios x main configuration, temperature 0.7, 5 loops   (FF2)
  det         3 reference scenarios x main configuration, temperature 0, 2 loops     (FF2, reproducibility)
  audit       one factor at a time away from the main configuration, 3 reference
              scenarios, temperature 0.7, 2 loops                                     (FF3 robustness)
  university  3 university variants (10 x 10) x main configuration, 5 loops          (only with --university)

Further stages that run only when they are named in --stages:

  university_audit  the audit factors, one at a time, applied to the 3 university variants,
                    temperature 0.7, 2 loops (--side-loops); respects --audit
  university_np     the 3 university variants without their statement on who takes part in which
                    body (scenarios university_*_no_participation), main configuration, 5 loops
                    (--core-loops); see docs/university_no_participation_diff.md

Main configuration = the notebook presets: prose, wording a, observer, canonical order, English,
pairwise, reason on, importance off, seed 0.

--scenarios restricts the core, det and audit stages to some of the three reference scenarios.

--thinking-level LEVEL sets the thinking level of a Gemini connector for this run and takes
precedence over GEMINI_THINKING_LEVEL and GEMINI_THINKING_BUDGET in .env ("default" sends no
thinking setting, so the model decides). --ollama-think true|false does the same for OLLAMA_THINK.
The setting is part of the connector identity and therefore of every cache key: answers obtained
with different settings are never mixed. Runs with one of these flags write to their own files
(..__think-<value>). The setting actually used is in the column "thinking" of the summary.

--seed N sets the base seed from which the seed of every call and the shuffled item orders are
derived. Seed 0 is the default and gives the requests that have been asked so far; any other seed
gives new requests and writes to its own files (..__seed<N>), so nothing is overwritten.

Every answered call is stored in the disk cache at once, so the script can be stopped with Ctrl+C
and restarted at any time; nothing is asked twice. Calls already made in the notebook with the same
settings are reused as well (for example the first loops of a notebook run).

A request that the server refuses as such (HTTP 4xx other than 408, 409, 425 and 429, for example
a thinking level the model does not accept, a wrong key or an unknown model) stops the script
after that one call and prints the server message in full. Rate limits (429), server errors (5xx)
and timeouts are retried and counted as before. --no-fail-fast restores the old behaviour, in
which every call of the configuration was tried before the script stopped.

Usage (from the repository root):

  uv run python scripts/run_batch.py --dry-run            # plan, cached vs. missing calls, no model call
  uv run python scripts/run_batch.py                      # core, det, audit with the only Ollama model
  uv run python scripts/run_batch.py --stages core det    # selected stages
  uv run python scripts/run_batch.py --connector mock     # pipeline test without a model
  uv run python scripts/run_batch.py --mode per_row --audit representation=role_list perspective=persona
  uv run python scripts/run_batch.py --mode per_row --stages core --seed 1   # a second, independent sample
  uv run python scripts/run_batch.py --mode per_row --stages audit --scenarios reference_hierarchical
  uv run python scripts/run_batch.py --mode per_row --stages university_audit --audit item_order=shuffled
  uv run python scripts/run_batch.py --mode per_row --stages university_np
  uv run python scripts/run_batch.py --connector gemini/<model> --mode per_row --stages core --thinking-level low
  uv run python scripts/run_batch.py --connector ollama/qwen3:4b --mode per_row --stages core --ollama-think false
  uv run python scripts/run_batch.py --no-fail-fast       # try every call even after an HTTP 4xx refusal

Output:
  data/llm_runs/*.jsonl                 raw answers, one file per complete configuration
  data/structures/batch/*.json          exported structure per complete configuration (threshold 0.5)
  data/batch/summary__<connector>.csv   one row per configuration: calls, invalid share, latency,
                                        distances to D0/D1/D2, kappa against the expected structure
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from gcm.contextual import aggregate as agg
from gcm.contextual.cache import DiskCache
from gcm.contextual.connectors import MockConnector, available_connectors
from gcm.contextual.connectors.registry import FROM_ENV, GEMINI_THINKING_LEVELS
from gcm.contextual.experiment import ExperimentConfig, n_calls, run_experiment
from gcm.contextual.paths import cache_dir, data_dir, runs_dir, structures_dir
from gcm.contextual.references import reference_matrices
from gcm.contextual.scenario import load_scenarios
from gcm.contextual.structure_io import StructureExport

REFERENCE = ["reference_hierarchical", "reference_specialized", "reference_unsegmented"]
UNIVERSITY = ["university_strong_power", "university_moderate_power", "university_weak_power"]
UNIVERSITY_NP = [f"{s}_no_participation" for s in UNIVERSITY]

MAIN = ExperimentConfig(scenario_id="", loops=5, temperature=0.7, seed=0)

# one factor at a time, in the order of their weight for the thesis
AUDIT = [
    ("representation", "role_list"),
    ("representation", "statute"),
    ("perspective", "persona"),
    ("wording", "b"),
    ("item_order", "shuffled"),
    ("language", "de"),
]


def plan(
    stages: list[str],
    main: ExperimentConfig,
    audit: list[tuple[str, str]],
    side_loops: int,
    reference: list[str] | None = None,
) -> list[tuple[str, str, ExperimentConfig]]:
    """The jobs of the given stages in priority order. ``reference`` restricts the reference
    scenarios of the core, det and audit stages (default: all three)."""
    reference = REFERENCE if reference is None else [s for s in REFERENCE if s in reference]
    jobs: list[tuple[str, str, ExperimentConfig]] = []
    if "core" in stages:
        jobs += [("core", s, replace(main, scenario_id=s)) for s in reference]
    if "det" in stages:
        jobs += [("det", s, replace(main, scenario_id=s, temperature=0.0, loops=side_loops)) for s in reference]
    if "audit" in stages:
        for name, level in audit:
            jobs += [
                (f"audit:{name}={level}", s, replace(main, scenario_id=s, loops=side_loops, **{name: level}))
                for s in reference
            ]
    if "university" in stages:
        jobs += [("university", s, replace(main, scenario_id=s)) for s in UNIVERSITY]
    if "university_audit" in stages:
        for name, level in audit:
            jobs += [
                (f"university_audit:{name}={level}", s, replace(main, scenario_id=s, loops=side_loops, **{name: level}))
                for s in UNIVERSITY
            ]
    if "university_np" in stages:
        jobs += [("university_np", s, replace(main, scenario_id=s)) for s in UNIVERSITY_NP]
    return jobs


def pick_connector(name: str | None, thinking_level: str | None = None, ollama_think: str | None = None):
    """Name and factory of the connector. ``thinking_level`` (a Gemini level or "default") and
    ``ollama_think`` ("true"/"false") override the settings of the environment."""
    if name == "mock":
        if thinking_level is not None or ollama_think is not None:
            sys.exit("--thinking-level and --ollama-think do not apply to the mock connector")
        return "mock", None
    factories = available_connectors(
        gemini_thinking_level=FROM_ENV if thinking_level is None
        else None if thinking_level == "default" else thinking_level,
        ollama_think=FROM_ENV if ollama_think is None else ollama_think == "true",
    )
    if name:
        if name not in factories:
            sys.exit(f"connector {name!r} not configured; available: {sorted(factories) or 'none (check .env)'}")
        return name, factories[name]
    ollama = [k for k in factories if k.startswith("ollama/")]
    if len(ollama) != 1:
        sys.exit(f"pass --connector, configured: {sorted(factories) or 'none (check .env)'}")
    return ollama[0], factories[ollama[0]]


def thinking_setting(identity: dict) -> str:
    """The thinking setting a connector sends, read from its identity (and so from the cache key)."""
    if identity.get("thinking_level") is not None:
        return f"level={identity['thinking_level']}"
    if identity.get("thinking_budget") is not None:
        return f"budget={identity['thinking_budget']}"
    if identity.get("think") is not None:
        return f"think={'true' if identity['think'] else 'false'}"
    if identity.get("connector") in ("gemini", "ollama"):
        return "model default"
    return ""


def summary_row(stage, scenario, cfg, result, connector_name) -> dict:
    est = agg.aggregate(result.records, scenario, label=cfg.label())
    share = est.share
    refs = reference_matrices(*scenario.shape)
    dist = agg.distances(share, refs).set_index("reference")["hamming_share"].to_dict()
    target = scenario.target_matrix()
    known = ~np.isnan(share)
    kappa = float("nan")
    if target is not None and known.all():
        kappa = agg.cohen_kappa(share >= 0.5, target)
    new = [r for r in result.records if not r["cached"] and r["latency_s"] is not None]
    lat = [r["latency_s"] for r in result.records if r["latency_s"] is not None]
    return {
        "stage": stage,
        "connector": connector_name,
        "model_ids": ";".join(result.model_ids),
        "scenario": scenario.id,
        "expected": scenario.expected or "",
        **{k: v for k, v in cfg.as_dict().items() if k != "scenario_id"},
        "calls": result.n_planned,
        "new_calls": len(new),
        "errors": result.n_errors,
        "invalid_share": round(est.invalid_share, 4),
        "mean_latency_s": round(float(np.mean(lat)), 3) if lat else "",
        "cells_undetermined": int((~known).sum()),
        "allowed_cells": int((share[known] >= 0.5).sum()),
        **{f"dist_{k}": round(v, 3) for k, v in dist.items()},
        "kappa_expected": round(kappa, 3) if not np.isnan(kappa) else "",
        "template_hash": result.template_hash,
        "config_hash": cfg.config_hash,
        # appended later; the columns above keep their names and their order
        "thinking": thinking_setting(result.identity),
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stages", nargs="+", default=["core", "det", "audit"],
                    choices=["core", "det", "audit", "university", "university_audit", "university_np"])
    ap.add_argument("--university", action="store_true", help="append the university stage")
    ap.add_argument("--connector", help="e.g. ollama/qwen3:8b, gemini/<model>, mock")
    ap.add_argument("--dry-run", action="store_true", help="count cached and missing calls only")
    ap.add_argument("--mode", choices=["pairwise", "per_row"], default="pairwise",
                    help="per_row asks about all opportunities of a participant in one call (10x fewer calls)")
    ap.add_argument("--core-loops", type=int, default=5, help="loops of the core, university and university_np stages")
    ap.add_argument("--side-loops", type=int, default=2, help="loops of the det, audit and university_audit stages")
    ap.add_argument("--scenarios", nargs="+", default=None, choices=REFERENCE, metavar="NAME",
                    help=f"reference scenarios of the core, det and audit stages, e.g. --scenarios "
                         f"reference_hierarchical; default all: {' '.join(REFERENCE)}")
    ap.add_argument("--thinking-level", choices=[*GEMINI_THINKING_LEVELS, "default"], default=None, metavar="LEVEL",
                    help=f"Gemini only: {', '.join(GEMINI_THINKING_LEVELS)} or default (= no thinking setting); "
                         "overrides GEMINI_THINKING_LEVEL/_BUDGET of .env, e.g. --thinking-level low")
    ap.add_argument("--ollama-think", choices=["true", "false"], default=None,
                    help="Ollama only: overrides OLLAMA_THINK of .env, e.g. --ollama-think false")
    ap.add_argument("--no-fail-fast", action="store_true",
                    help="do not stop at the first call the server refuses with HTTP 4xx (the behaviour before)")
    ap.add_argument("--seed", type=int, default=0, metavar="N",
                    help="base seed of all stages (default 0 = the runs made so far); other seeds write to "
                         "files with the suffix __seed<N>, e.g. --seed 1")
    ap.add_argument("--audit", nargs="+", default=None, metavar="FACTOR=LEVEL",
                    help=f"subset of the audit (stages audit and university_audit), e.g. representation=role_list perspective=persona; "
                         f"default all: {' '.join(f'{n}={l}' for n, l in AUDIT)}")
    args = ap.parse_args(argv)

    stages = list(args.stages) + (["university"] if args.university and "university" not in args.stages else [])
    scenarios = load_scenarios()
    audit = AUDIT if args.audit is None else [tuple(a.split("=", 1)) for a in args.audit]
    unknown = [a for a in audit if a not in AUDIT]
    if unknown:
        sys.exit(f"unknown audit levels {unknown}; choose from {AUDIT}")
    if args.seed < 0:
        sys.exit("--seed must not be negative")
    main_cfg = replace(MAIN, mode=args.mode, loops=args.core_loops, seed=args.seed)
    jobs = plan(stages, main_cfg, audit, args.side_loops, args.scenarios)
    connector_name, factory = pick_connector(args.connector, args.thinking_level, args.ollama_think)
    if args.thinking_level is not None and not connector_name.startswith("gemini/"):
        sys.exit(f"--thinking-level applies to gemini/<model> connectors only, not to {connector_name}")
    if args.ollama_think is not None and not connector_name.startswith("ollama/"):
        sys.exit(f"--ollama-think applies to ollama/<model> connectors only, not to {connector_name}")
    override = args.thinking_level if args.thinking_level is not None else args.ollama_think
    cache = DiskCache(cache_dir())
    out_dir = data_dir() / "batch"
    out_dir.mkdir(parents=True, exist_ok=True)
    struct_dir = structures_dir() / "batch"
    slug = re.sub(r"[^A-Za-z0-9.]+", "-", connector_name).strip("-")
    # Without the new flags the file names are the ones used so far. A thinking setting given on
    # the command line and a seed other than 0 get their own files, because the names of the
    # summary and of the structures carry neither the connector identity nor the seed otherwise.
    suffix = (f"__think-{override}" if override is not None else "") + (f"__seed{args.seed}" if args.seed else "")
    summary_path = out_dir / f"summary__{slug}{suffix}.csv"  # one file per connector, so runs can go in parallel

    def make(scenario, cfg):
        if factory is None:
            return MockConnector.for_scenario(scenario, noise=0.1, seed=cfg.seed)
        return factory()

    # plan with cache status
    total = missing = 0
    print(f"connector: {connector_name}  mode: {args.mode}"
          + (f"  thinking: {override}" if override is not None else "")
          + (f"  seed: {args.seed}" if args.seed else ""))
    for stage, sid, cfg in jobs:
        s = scenarios[sid]
        res = run_experiment(s, cfg, make(s, cfg), cache=cache, cache_only=True)
        total += res.n_planned
        missing += res.n_missing
        print(f"  {stage:28s} {sid:28s} {res.n_planned:5d} calls, {res.n_missing:5d} missing")
    print(f"total {total} calls, {missing} still to ask")
    if args.dry_run or missing == 0 and summary_path.exists():
        if not args.dry_run:
            print("everything cached; rewriting the summary")
        else:
            return

    rows, done, t0 = [], 0, time.time()
    for i, (stage, sid, cfg) in enumerate(jobs, 1):
        s = scenarios[sid]
        print(f"[{i}/{len(jobs)}] {stage} {sid} {cfg.label()} T={cfg.temperature} loops={cfg.loops}", flush=True)
        last = [time.time()]

        def progress(k, n, _last=last):
            if time.time() - _last[0] > 60 or k == n:
                _last[0] = time.time()
                print(f"    {k}/{n}", flush=True)

        res = run_experiment(s, cfg, make(s, cfg), cache=cache, log_dir=runs_dir(), progress=progress,
                             stop_on_config_error=not args.no_fail_fast)
        done += res.n_new
        if res.config_error is not None:
            sys.exit(f"the server refused a request of {stage} {sid} as such; stopping after {res.n_new} new "
                     f"call(s), {res.n_missing} not asked. This is a configuration error (model name, key, "
                     f"thinking level, output format), not a quota or a server problem. "
                     f"Answers so far are cached.\nServer message:\n{res.config_error}")
        rows.append(summary_row(stage, s, cfg, res, connector_name))
        if res.n_errors:
            print(f"    {res.n_errors} failed calls (not cached, asked again on the next start)")
            last_error = next((r["error"] for r in reversed(res.records) if r["error"]), "")
            print(f"    last error: {str(last_error)[:200]}")
        new_ok = sum(1 for r in res.records if not r["cached"] and not r["error"])
        if res.n_new >= 10 and new_ok == 0:
            sys.exit("every new call of this configuration failed (daily quota, key or connection?); stopping. "
                     "Answers so far are cached; start again later.")
        try:
            export = StructureExport.from_estimate(
                agg.aggregate(res.records, s, label=cfg.label()), s, threshold=0.5,
                on_missing="error", name=f"{connector_name} | {cfg.label()} | T={cfg.temperature}",
            )
            name = re.sub(r"[^A-Za-z0-9.]+", "-", f"{sid}__{connector_name}__{cfg.config_hash}{suffix}").strip("-")
            export.save(struct_dir / f"{name}.json")
        except agg.UndeterminedCellsError as exc:
            print(f"    structure not exported: {exc}")
        with summary_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        lat = [r["latency_s"] for r in res.records if not r["cached"] and r["latency_s"] is not None]
        if lat:
            print(f"    model time per new call: mean {np.mean(lat):.1f} s, median {np.median(lat):.1f} s", flush=True)
        if done and missing:
            rate = (time.time() - t0) / done
            left = max(0, missing - done) * rate
            print(f"    {done}/{missing} new calls, {rate:.1f} s wall time per call, about {left / 3600:.1f} h left", flush=True)
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
