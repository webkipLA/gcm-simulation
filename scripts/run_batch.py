"""Batch run of the contextual decision structure without the notebook.

Runs a fixed, bounded design in priority order, so that an interrupted night still leaves the
most important configurations complete:

  core        3 reference scenarios x main configuration, temperature 0.7, 5 loops   (FF2)
  det         3 reference scenarios x main configuration, temperature 0, 2 loops     (FF2, reproducibility)
  audit       one factor at a time away from the main configuration, 3 reference
              scenarios, temperature 0.7, 2 loops                                     (FF3 robustness)
  university  3 university variants (10 x 10) x main configuration, 5 loops          (only with --university)

Main configuration = the notebook presets: prose, wording a, observer, canonical order, English,
pairwise, reason on, importance off, seed 0.

Every answered call is stored in the disk cache at once, so the script can be stopped with Ctrl+C
and restarted at any time; nothing is asked twice. Calls already made in the notebook with the same
settings are reused as well (for example the first loops of a notebook run).

Usage (from the repository root):

  uv run python scripts/run_batch.py --dry-run            # plan, cached vs. missing calls, no model call
  uv run python scripts/run_batch.py                      # core, det, audit with the only Ollama model
  uv run python scripts/run_batch.py --stages core det    # selected stages
  uv run python scripts/run_batch.py --connector mock     # pipeline test without a model
  uv run python scripts/run_batch.py --mode per_row --audit representation=role_list perspective=persona

Output:
  data/llm_runs/*.jsonl                 raw answers, one file per complete configuration
  data/structures/batch/*.json          exported structure per complete configuration (threshold 0.5)
  data/batch/summary.csv                one row per configuration: calls, invalid share, latency,
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
from gcm.contextual.experiment import ExperimentConfig, n_calls, run_experiment
from gcm.contextual.paths import cache_dir, data_dir, runs_dir, structures_dir
from gcm.contextual.references import reference_matrices
from gcm.contextual.scenario import load_scenarios
from gcm.contextual.structure_io import StructureExport

REFERENCE = ["reference_hierarchical", "reference_specialized", "reference_unsegmented"]
UNIVERSITY = ["university_strong_power", "university_moderate_power", "university_weak_power"]

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


def plan(stages: list[str], main: ExperimentConfig, audit: list[tuple[str, str]], side_loops: int) -> list[tuple[str, str, ExperimentConfig]]:
    jobs: list[tuple[str, str, ExperimentConfig]] = []
    if "core" in stages:
        jobs += [("core", s, replace(main, scenario_id=s)) for s in REFERENCE]
    if "det" in stages:
        jobs += [("det", s, replace(main, scenario_id=s, temperature=0.0, loops=side_loops)) for s in REFERENCE]
    if "audit" in stages:
        for name, level in audit:
            jobs += [
                (f"audit:{name}={level}", s, replace(main, scenario_id=s, loops=side_loops, **{name: level}))
                for s in REFERENCE
            ]
    if "university" in stages:
        jobs += [("university", s, replace(main, scenario_id=s)) for s in UNIVERSITY]
    return jobs


def pick_connector(name: str | None):
    if name == "mock":
        return "mock", None
    factories = available_connectors()
    if name:
        if name not in factories:
            sys.exit(f"connector {name!r} not configured; available: {sorted(factories) or 'none (check .env)'}")
        return name, factories[name]
    ollama = [k for k in factories if k.startswith("ollama/")]
    if len(ollama) != 1:
        sys.exit(f"pass --connector, configured: {sorted(factories) or 'none (check .env)'}")
    return ollama[0], factories[ollama[0]]


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
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stages", nargs="+", default=["core", "det", "audit"],
                    choices=["core", "det", "audit", "university"])
    ap.add_argument("--university", action="store_true", help="append the university stage")
    ap.add_argument("--connector", help="e.g. ollama/qwen3:8b, gemini/<model>, mock")
    ap.add_argument("--dry-run", action="store_true", help="count cached and missing calls only")
    ap.add_argument("--mode", choices=["pairwise", "per_row"], default="pairwise",
                    help="per_row asks about all opportunities of a participant in one call (10x fewer calls)")
    ap.add_argument("--core-loops", type=int, default=5, help="loops of the core and university stages")
    ap.add_argument("--side-loops", type=int, default=2, help="loops of the det and audit stages")
    ap.add_argument("--audit", nargs="+", default=None, metavar="FACTOR=LEVEL",
                    help=f"subset of the audit, e.g. representation=role_list perspective=persona; "
                         f"default all: {' '.join(f'{n}={l}' for n, l in AUDIT)}")
    args = ap.parse_args()

    stages = list(args.stages) + (["university"] if args.university and "university" not in args.stages else [])
    scenarios = load_scenarios()
    audit = AUDIT if args.audit is None else [tuple(a.split("=", 1)) for a in args.audit]
    unknown = [a for a in audit if a not in AUDIT]
    if unknown:
        sys.exit(f"unknown audit levels {unknown}; choose from {AUDIT}")
    main_cfg = replace(MAIN, mode=args.mode, loops=args.core_loops)
    jobs = plan(stages, main_cfg, audit, args.side_loops)
    connector_name, factory = pick_connector(args.connector)
    cache = DiskCache(cache_dir())
    out_dir = data_dir() / "batch"
    out_dir.mkdir(parents=True, exist_ok=True)
    struct_dir = structures_dir() / "batch"
    summary_path = out_dir / "summary.csv"

    def make(scenario, cfg):
        if factory is None:
            return MockConnector.for_scenario(scenario, noise=0.1, seed=cfg.seed)
        return factory()

    # plan with cache status
    total = missing = 0
    print(f"connector: {connector_name}  mode: {args.mode}")
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

        res = run_experiment(s, cfg, make(s, cfg), cache=cache, log_dir=runs_dir(), progress=progress)
        done += res.n_new
        rows.append(summary_row(stage, s, cfg, res, connector_name))
        if res.n_errors:
            print(f"    {res.n_errors} failed calls (not cached, asked again on the next start)")
        try:
            export = StructureExport.from_estimate(
                agg.aggregate(res.records, s, label=cfg.label()), s, threshold=0.5,
                on_missing="error", name=f"{connector_name} | {cfg.label()} | T={cfg.temperature}",
            )
            name = re.sub(r"[^A-Za-z0-9.]+", "-", f"{sid}__{connector_name}__{cfg.config_hash}").strip("-")
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
