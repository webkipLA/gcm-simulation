"""Simulation comparison: baselines and contextual structures under identical conditions.

FORTRAN
    The program is deterministic. A *condition* is one decision structure; it is run over the
    paper's situations (loads × access structures × energy distributions × entry conditions),
    so every condition sees exactly the same 108 situations. In sampling mode the contextual
    structure is drawn once per situation with a seed derived from the situation index.

NetLogo
    A *condition* is one decision structure plus the settings of the other two structures. All
    conditions are run with the same list of seeds, so the baseline and the contextual variant
    start from the same agents at the same positions. Runs are distributed over processes; the
    conditions are plain dataclasses, so they pickle.

Statistics
    Decision styles are compared with a chi-square test on the pooled contingency table
    (condition × style) with Cramér's V as effect size. Metrics are compared per condition
    against a baseline with the mean, a bootstrap confidence interval over runs, the
    difference of means with its bootstrap interval, Cohen's d and a Mann-Whitney U test.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd
from scipy import stats

from gcm.common import StructureKind
from gcm.contextual.fortran_adapter import ContextualDecisionStructure
from gcm.contextual.metrics import (
    ObservedGarbageCanABM,
    fortran_level_metrics,
    netlogo_level_metrics,
)
from gcm.contextual.netlogo_adapter import ContextualNetLogoDecisionStructure, RoleAssignment
from gcm.contextual.structure_io import StructureExport
from gcm.fortran import data as fortran_data
from gcm.fortran.model import FortranComponents, GarbageCanFortran
from gcm.fortran.parameters import FortranParameters, Load
from gcm.fortran.statistics import summarise
from gcm.fortran.structures import decision_structure
from gcm.netlogo.model import NetLogoComponents
from gcm.netlogo.parameters import NetLogoParameters, Structure


# ------------------------------------------------------------------------------------ FORTRAN
@dataclass(frozen=True)
class FortranCondition:
    """One decision structure to run over the paper's situations."""

    name: str
    kind: StructureKind | None = None  # rule-based reference, or
    export: StructureExport | None = None  # a contextual structure
    mode: str = "threshold"  # for exports: threshold | sample

    def component(self, params: FortranParameters, situation: int):
        if self.export is not None:
            seed = situation if self.mode == "sample" else None
            return ContextualDecisionStructure(
                self.export,
                mode=self.mode,
                seed=seed,
                n_choices=params.n_choices,
                n_decision_makers=params.n_decision_makers,
            )
        return decision_structure(self.kind, params.n_choices, params.n_decision_makers)


def fortran_reference_conditions() -> list[FortranCondition]:
    return [FortranCondition(f"D_{k.value}", kind=k) for k in StructureKind]


def run_fortran_conditions(
    conditions: Sequence[FortranCondition],
    *,
    loads: Iterable[Load] = tuple(Load),
    accesses: Iterable[StructureKind] = tuple(StructureKind),
    energies: Iterable[int] = (0, 1, 2),
    entry_conditions: Iterable[str] = tuple(fortran_data.ENTRY_CONDITIONS),
    n_levels: int = 2,
    arithmetic: str = "exact",
) -> pd.DataFrame:
    """One row per condition × situation with the summary statistics and per-level metrics."""
    rows = []
    situations = [
        (cond_name, load, access, energy)
        for cond_name in entry_conditions
        for load in loads
        for access in accesses
        for energy in energies
    ]
    for condition in conditions:
        for index, (entry, load, access, energy) in enumerate(situations):
            params = FortranParameters.from_entry_condition(entry, arithmetic=arithmetic)
            comps = FortranComponents.classic(access=access, energy=energy, params=params)
            comps.decision_structure = condition.component(params, index)
            model = GarbageCanFortran(params, load, comps)
            history = model.run()
            stats_ = summarise(
                history, model.energy_reserve, model.energy_wastage, model.state.dm_resting_periods
            )
            rows.append(
                {
                    "condition": condition.name,
                    "situation": index,
                    "entry_condition": entry,
                    "load": load.name.lower(),
                    "access": access.value,
                    "energy": energy,
                    "decision_structure": comps.decision_structure.name,
                    **stats_.as_dict(),
                    **fortran_level_metrics(history, n_levels),
                }
            )
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------ NetLogo
@dataclass(frozen=True)
class NetLogoCondition:
    """One decision structure plus the parameters it runs with."""

    name: str
    params: NetLogoParameters
    export: StructureExport | None = None  # None = the rule-based chooser of ``params``
    assignment: RoleAssignment | None = None
    mode: str = "threshold"
    levels: str = "divide"

    def with_other_structures(self, structure: Structure) -> NetLogoCondition:
        """The same condition with availability and access structure set to ``structure``."""
        return replace(
            self,
            params=replace(
                self.params, availability_structure=structure, access_structure=structure
            ),
        )

    def build(self, seed: int) -> ObservedGarbageCanABM:
        params = replace(self.params, seed=seed)
        comps = NetLogoComponents.classic(params)
        if self.export is not None:
            comps.decision_structure = ContextualNetLogoDecisionStructure(
                self.export,
                self.assignment,
                mode=self.mode,
                seed=seed if self.mode == "sample" else None,
            )
        return ObservedGarbageCanABM(params, components=comps, record_events=True)


def _run_netlogo(args: tuple[NetLogoCondition, int, int]) -> dict:
    condition, seed, ticks = args
    model = condition.build(seed)
    results = model.run(ticks)
    return {
        "condition": condition.name,
        "seed": seed,
        "decision_structure": model.components.decision_structure.name,
        "availability_structure": condition.params.availability_structure.value,
        "access_structure": condition.params.access_structure.value,
        "postpone": condition.params.postpone,
        "buckpass": condition.params.buckpass,
        **results.as_dict(),
        **netlogo_level_metrics(model, condition.levels),
    }


def run_netlogo_conditions(
    conditions: Sequence[NetLogoCondition],
    seeds: Iterable[int],
    ticks: int,
    workers: int = 1,
) -> pd.DataFrame:
    """One row per condition × seed. Every condition is run with every seed."""
    jobs = [(c, int(seed), ticks) for c in conditions for seed in seeds]
    if workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_run_netlogo, jobs))
    else:
        rows = [_run_netlogo(job) for job in jobs]
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------ tests
FORTRAN_STYLES = ("by_resolution", "by_oversight", "by_flight")
NETLOGO_STYLES = ("num_resolutions", "num_oversights")


def style_table(results: pd.DataFrame, styles: Sequence[str] = FORTRAN_STYLES) -> pd.DataFrame:
    """Pooled counts per condition and decision style, plus shares."""
    counts = results.groupby("condition", sort=False)[list(styles)].sum()
    shares = counts.div(counts.sum(axis=1), axis=0).add_suffix("_share")
    return pd.concat([counts, shares], axis=1)


def cramers_v(table: np.ndarray) -> float:
    table = np.asarray(table, dtype=float)
    n = table.sum()
    if n == 0 or min(table.shape) < 2:
        return float("nan")
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    return float(np.sqrt(chi2 / (n * (min(table.shape) - 1))))


@dataclass
class ChiSquareResult:
    table: pd.DataFrame
    chi2: float
    p_value: float
    dof: int
    cramers_v: float
    expected: pd.DataFrame = field(repr=False)

    def as_dict(self) -> dict:
        return {
            "chi2": self.chi2,
            "p_value": self.p_value,
            "dof": self.dof,
            "cramers_v": self.cramers_v,
            "n": int(self.table.to_numpy().sum()),
        }


def style_chi_square(
    results: pd.DataFrame,
    styles: Sequence[str] = FORTRAN_STYLES,
    conditions: Sequence[str] | None = None,
) -> ChiSquareResult:
    """Chi-square test of independence between condition and decision style on pooled counts.

    Columns with zero total are dropped (a style that never occurs carries no information).
    """
    table = results.groupby("condition", sort=False)[list(styles)].sum()
    if conditions is not None:
        table = table.loc[list(conditions)]
    table = table.loc[:, table.sum(axis=0) > 0]
    table = table.loc[table.sum(axis=1) > 0]
    if table.shape[0] < 2 or table.shape[1] < 2:
        nan = float("nan")
        return ChiSquareResult(table, nan, nan, 0, nan, table * nan)
    chi2, p, dof, expected = stats.chi2_contingency(table.to_numpy(), correction=False)
    return ChiSquareResult(
        table,
        float(chi2),
        float(p),
        int(dof),
        cramers_v(table.to_numpy()),
        pd.DataFrame(expected, index=table.index, columns=table.columns),
    )


def bootstrap_ci(
    values: Sequence[float],
    *,
    n_boot: int = 2000,
    level: float = 0.95,
    seed: int = 0,
    statistic=np.mean,
) -> tuple[float, float]:
    """Percentile bootstrap interval of ``statistic`` over ``values`` (NaNs dropped)."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return float("nan"), float("nan")
    if len(values) == 1:
        return float(values[0]), float(values[0])
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(n_boot, len(values)), replace=True)
    boot = np.apply_along_axis(statistic, 1, draws)
    alpha = (1 - level) / 2
    return float(np.quantile(boot, alpha)), float(np.quantile(boot, 1 - alpha))


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    pooled = np.sqrt(
        ((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2)
    )
    return float((a.mean() - b.mean()) / pooled) if pooled > 0 else float("nan")


def compare_metrics(
    results: pd.DataFrame,
    metrics: Sequence[str],
    baseline: str,
    *,
    paired_on: str | None = None,
    n_boot: int = 2000,
    seed: int = 0,
) -> pd.DataFrame:
    """Every condition against ``baseline``, per metric.

    With ``paired_on`` (``"seed"`` for NetLogo, ``"situation"`` for FORTRAN) the difference is
    computed within pairs and its interval bootstraps the paired differences; otherwise the
    interval bootstraps the difference of independent means. The p-value is from a two-sided
    Mann-Whitney U test (Wilcoxon signed-rank when paired).
    """
    rows = []
    base = results[results["condition"] == baseline]
    for condition in results["condition"].unique():
        here = results[results["condition"] == condition]
        for metric in metrics:
            x, y = here[metric].to_numpy(dtype=float), base[metric].to_numpy(dtype=float)
            row = {
                "condition": condition,
                "metric": metric,
                "n": int(np.sum(~np.isnan(x))),
                "mean": float(np.nanmean(x)) if np.any(~np.isnan(x)) else float("nan"),
            }
            row["ci_low"], row["ci_high"] = bootstrap_ci(x, n_boot=n_boot, seed=seed)
            row["baseline_mean"] = float(np.nanmean(y)) if np.any(~np.isnan(y)) else float("nan")
            if paired_on is not None:
                merged = here[[paired_on, metric]].merge(
                    base[[paired_on, metric]], on=paired_on, suffixes=("", "_base")
                )
                diff = (merged[metric] - merged[f"{metric}_base"]).to_numpy(dtype=float)
                diff = diff[~np.isnan(diff)]
                row["difference"] = float(diff.mean()) if len(diff) else float("nan")
                row["diff_ci_low"], row["diff_ci_high"] = bootstrap_ci(
                    diff, n_boot=n_boot, seed=seed
                )
                nonzero = diff[diff != 0]
                if condition == baseline or len(nonzero) == 0:
                    row["p_value"] = float("nan") if condition == baseline else 1.0
                else:
                    row["p_value"] = float(stats.wilcoxon(nonzero).pvalue)
            else:
                row["difference"] = row["mean"] - row["baseline_mean"]
                rng = np.random.default_rng(seed)
                xs, ys = x[~np.isnan(x)], y[~np.isnan(y)]
                if len(xs) and len(ys):
                    boot = rng.choice(xs, (n_boot, len(xs))).mean(axis=1) - rng.choice(
                        ys, (n_boot, len(ys))
                    ).mean(axis=1)
                    row["diff_ci_low"], row["diff_ci_high"] = (
                        float(np.quantile(boot, 0.025)),
                        float(np.quantile(boot, 0.975)),
                    )
                else:
                    row["diff_ci_low"] = row["diff_ci_high"] = float("nan")
                if condition == baseline or len(xs) < 1 or len(ys) < 1:
                    row["p_value"] = float("nan")
                else:
                    row["p_value"] = float(
                        stats.mannwhitneyu(xs, ys, alternative="two-sided").pvalue
                    )
            row["cohens_d"] = cohens_d(x, y)
            rows.append(row)
    return pd.DataFrame(rows)


__all__ = [
    "FORTRAN_STYLES",
    "NETLOGO_STYLES",
    "ChiSquareResult",
    "FortranCondition",
    "NetLogoCondition",
    "bootstrap_ci",
    "cohens_d",
    "compare_metrics",
    "cramers_v",
    "fortran_reference_conditions",
    "run_fortran_conditions",
    "run_netlogo_conditions",
    "style_chi_square",
    "style_table",
]
