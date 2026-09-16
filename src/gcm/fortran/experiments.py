"""Experiment drivers: the 324 simulation situations of the paper and its summary tables."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from gcm.common import StructureKind
from gcm.fortran import data
from gcm.fortran.model import FortranComponents, GarbageCanFortran
from gcm.fortran.parameters import FortranParameters, Load, MovementCondition
from gcm.fortran.statistics import SummaryStatistics, summarise
from gcm.fortran.structures import OrganizationalVariant

_LOAD_NAMES = {0: "light", 1: "moderate", 2: "heavy"}
_ENERGY_NAMES = {0: "important_less", 1: "equal", 2: "important_more"}


def run_variant(
    variant: OrganizationalVariant,
    params: FortranParameters,
    components: FortranComponents | None = None,
) -> tuple[GarbageCanFortran, SummaryStatistics]:
    """Run one organizational variant under one entry-time condition."""
    comps = components or FortranComponents.classic(
        access=variant.access, decision=variant.decision, energy=variant.energy, params=params
    )
    model = GarbageCanFortran(params, Load(variant.load), comps)
    hist = model.run()
    stats = summarise(
        hist, model.energy_reserve, model.energy_wastage, model.state.dm_resting_periods
    )
    return model, stats


def run_all(
    entry_conditions: Iterable[str] = tuple(data.ENTRY_CONDITIONS),
    variants: Iterable[OrganizationalVariant] | None = None,
    movement: MovementCondition = MovementCondition.BOTH_MOVE,
    solution_coefficients: tuple[float, ...] = data.SOLUTION_COEFFICIENTS_CONSTANT,
    arithmetic: str = "exact",
    **param_overrides,
) -> pd.DataFrame:
    """Run every variant × entry condition (324 runs by default) and tabulate the statistics."""
    rows = []
    variants = list(variants) if variants is not None else OrganizationalVariant.all()
    for cond in entry_conditions:
        params = FortranParameters.from_entry_condition(
            cond,
            movement=movement,
            solution_coefficients=solution_coefficients,
            arithmetic=arithmetic,
            **param_overrides,
        )
        for v in variants:
            _, stats = run_variant(v, params)
            rows.append(
                {
                    "entry_condition": cond,
                    "code": v.code,
                    "load": _LOAD_NAMES[v.load],
                    "access": v.access.value,
                    "decision": v.decision.value,
                    "energy": _ENERGY_NAMES[v.energy],
                    **stats.as_dict(),
                }
            )
    return pd.DataFrame(rows)


_LOAD_ORDER = ["light", "moderate", "heavy"]
_STRUCT_ORDER = [
    k.value
    for k in (StructureKind.UNSEGMENTED, StructureKind.HIERARCHICAL, StructureKind.SPECIALIZED)
]


def table_1(results: pd.DataFrame, pooled: bool = True) -> pd.DataFrame:
    """Proportion of choices that resolve problems, by load and access structure (paper Table 1).

    ``pooled=True`` divides total resolutions by total choices made within each cell;
    ``pooled=False`` averages the per-run proportions. The paper does not say which it used.
    """
    df = results.copy()

    def cell(g: pd.DataFrame) -> float:
        if pooled:
            return g["by_resolution"].sum() / g["choices_made"].sum()
        return g["proportion_resolution"].mean()

    body = df.groupby(["load", "access"]).apply(cell, include_groups=False).unstack("access")
    body["all"] = df.groupby("load").apply(cell, include_groups=False)
    total = pd.Series(
        {a: cell(df[df["access"] == a]) for a in _STRUCT_ORDER} | {"all": cell(df)}, name="all"
    )
    body = pd.concat([body, total.to_frame().T])
    return body.reindex(index=_LOAD_ORDER + ["all"], columns=["all"] + _STRUCT_ORDER).round(2)


TABLE_1_PUBLISHED = pd.DataFrame(
    {
        "all": [0.55, 0.30, 0.36, 0.40],
        "unsegmented": [0.38, 0.04, 0.35, 0.26],
        "hierarchical": [0.61, 0.27, 0.23, 0.37],
        "specialized": [0.65, 0.60, 0.50, 0.58],
    },
    index=_LOAD_ORDER + ["all"],
)
"""Table 1 as printed in Cohen, March & Olsen (1972, p. 9)."""


def table_2(results: pd.DataFrame) -> pd.DataFrame:
    """Effects of variations in load (paper Table 2)."""
    g = results.groupby("load")
    out = pd.DataFrame(
        {
            "mean_problem_activity": g["problem_persistence"].mean(),
            "mean_dm_activity": g["dm_velocity"].mean(),
            "mean_decision_difficulty": g["choice_persistence"].mean(),
            "proportion_flight_or_oversight": g["by_flight"].sum().add(g["by_oversight"].sum())
            / g["choices_made"].sum(),
        }
    )
    return out.reindex(_LOAD_ORDER).round(2)


TABLE_2_PUBLISHED = pd.DataFrame(
    {
        "mean_problem_activity": [114.9, 204.3, 211.1],
        "mean_dm_activity": [60.9, 63.8, 76.6],
        "mean_decision_difficulty": [19.5, 32.9, 46.1],
        "proportion_flight_or_oversight": [0.45, 0.70, 0.64],
    },
    index=_LOAD_ORDER,
)
"""Table 2 as printed in Cohen, March & Olsen (1972, p. 10)."""


def table_5_rows(results: pd.DataFrame, codes: Iterable[str]) -> pd.DataFrame:
    """Statistics for selected organizational codes, averaged over the four entry conditions
    (the layout of paper Table 5: proportion resolution, problem activity, latency, decision maker
    activity, decision time)."""
    sub = results[results["code"].isin(list(codes))]
    g = sub.groupby("code")
    return pd.DataFrame(
        {
            "proportion_resolution": g["by_resolution"].sum() / g["choices_made"].sum(),
            "problem_activity": g["problem_persistence"].mean(),
            "problem_latency": g["problem_latency"].mean(),
            "dm_activity": g["dm_velocity"].mean(),
            "decision_time": g["choice_persistence"].mean(),
        }
    ).round(2)
