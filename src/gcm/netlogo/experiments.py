"""Experiment drivers for the NetLogo model (the BehaviorSpace experiments and custom grids)."""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import pandas as pd

from gcm.netlogo.model import GarbageCanABM
from gcm.netlogo.parameters import NetLogoParameters, behavior_space_experiments


def _run_one(args: tuple[str, NetLogoParameters, int, int | None]) -> dict:
    name, params, seed, ticks = args
    model = GarbageCanABM(replace(params, seed=seed), record_events=False)
    res = model.run(ticks)
    return {"experiment": name, "seed": seed, **_describe(params), **res.as_dict()}


def _describe(p: NetLogoParameters) -> dict:
    return {
        "decision_structure": p.decision_structure.value,
        "availability_structure": p.availability_structure.value,
        "access_structure": p.access_structure.value,
        "postpone": p.postpone,
        "buckpass": p.buckpass,
        "n_participants": p.number_of_participants,
        "n_opportunities": p.number_of_opportunities,
        "n_solutions": p.number_of_solutions,
        "n_problems": p.number_of_problems,
    }


def run_experiments(
    experiments: dict[str, NetLogoParameters] | None = None,
    repetitions: int = 3,
    ticks: int | None = None,
    seed0: int = 0,
    workers: int = 1,
) -> pd.DataFrame:
    """Run each experiment ``repetitions`` times with seeds ``seed0, seed0 + 1, …``.

    ``ticks`` overrides ``stop_at`` (the BehaviorSpace default of 50 000 ticks takes about a
    minute per run in pure Python; 2 000–5 000 ticks give a quick impression).
    """
    experiments = experiments or behavior_space_experiments()
    jobs = [
        (name, p, seed0 + i, ticks) for name, p in experiments.items() for i in range(repetitions)
    ]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            rows = list(ex.map(_run_one, jobs))
    else:
        rows = [_run_one(j) for j in jobs]
    return pd.DataFrame(rows)


def summarise_experiments(results: pd.DataFrame) -> pd.DataFrame:
    """Mean and standard deviation of the main indicators per experiment."""
    cols = [
        "num_resolutions",
        "num_oversights",
        "share_resolutions",
        "num_postponements",
        "num_buck_passings",
        "num_blocked_resolutions",
        "num_blocked_oversights",
        "ave_duration_blocked",
        "ave_duration_postponed",
        "ave_duration_passed",
        "num_resolutions_high",
        "num_resolutions_low",
        "num_oversights_high",
        "num_oversights_low",
    ]
    g = results.groupby("experiment", sort=False)
    out = g[cols].mean().round(3)
    out["n_runs"] = g.size()
    out["share_resolutions_sd"] = g["share_resolutions"].std().round(4)
    return out


def sweep(
    base: NetLogoParameters,
    values: Iterable,
    field: str,
    repetitions: int = 3,
    ticks: int | None = None,
    seed0: int = 0,
    workers: int = 1,
) -> pd.DataFrame:
    """One-factor sweep over ``field`` of :class:`NetLogoParameters`."""
    exps = {f"{field}={v}": replace(base, **{field: v}) for v in values}
    df = run_experiments(exps, repetitions=repetitions, ticks=ticks, seed0=seed0, workers=workers)
    df[field] = [exps[n].__dict__[field] for n in df["experiment"]]
    return df
