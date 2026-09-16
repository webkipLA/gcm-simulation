"""The ten summary statistics of the FORTRAN program plus the paper's decision-style measure.

The accumulation loops (labels 310–380) are reproduced literally, including a quirk of the
original: the problem statistics ``KT`` / ``KU`` / ``KW`` and the velocities ``KV`` / ``KX``
are accumulated from period **2** onwards (``DO 330 I = 2, NTP``), so period 1 is never counted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from gcm.common import DecisionStyle
from gcm.fortran.model import FortranHistory
from gcm.fortran.state import ACTIVE, NOT_ENTERED_MARK, SOLVED_MARK


@dataclass(frozen=True)
class SummaryStatistics:
    """Columns 1–10 of the program's output line, in the program's order, plus decision styles."""

    choices_not_made: int  # KZ  "decision difficulty" (alternative measure)
    choice_persistence: int  # KY  "decision difficulty" (measure used in the paper)
    dm_velocity: int  # KX  "decision maker activity" (measure used in the paper)
    problems_not_solved: int  # KW
    problem_velocity: int  # KV
    problem_latency: int  # KU  (measure used in the paper)
    problem_persistence: int  # KT  "problem activity" (measure used in the paper)
    dm_inactivity: int  # KS
    energy_reserve: float  # XR
    energy_wastage: float  # XS
    # --- decision style (paper pp. 8–9; not printed by the program) ---
    choices_made: int
    by_resolution: int
    by_oversight: int
    by_flight: int

    @property
    def proportion_resolution(self) -> float:
        return self.by_resolution / self.choices_made if self.choices_made else float("nan")

    @property
    def proportion_flight_or_oversight(self) -> float:
        return (
            (self.by_flight + self.by_oversight) / self.choices_made
            if self.choices_made
            else float("nan")
        )

    def as_dict(self) -> dict:
        d = asdict(self)
        d["proportion_resolution"] = self.proportion_resolution
        d["proportion_flight_or_oversight"] = self.proportion_flight_or_oversight
        return d


def summarise(
    history: FortranHistory, energy_reserve: float, energy_wastage: float, dm_resting: int
) -> SummaryStatistics:
    """Compute the ten summary statistics from the histories exactly like labels 310–380."""
    kabc, kbbc, kcbc = history.choices, history.decision_makers, history.problems
    ntp = kabc.shape[0]
    n_problems = kcbc.shape[1]

    # KY / KZ (labels 310–320): active choice-periods; choices still active in the last period.
    active = kabc == ACTIVE
    ky = int(active.sum())
    kz = int(active[ntp - 1].sum())

    # KX (labels 330–340): decision-maker changes, periods 2..NTP.
    kx = int((kbbc[1:] != kbbc[:-1]).sum())

    # KT / KU / KW (labels 350–360), periods 2..NTP only.
    later = kcbc[1:]
    ku = int((later == 0).sum())  # latent: entered but unattached
    kt = int(((later != 0) & (later != NOT_ENTERED_MARK) & (later != SOLVED_MARK)).sum())
    solved_at_end = int((kcbc[ntp - 1] == SOLVED_MARK).sum())
    kw = n_problems - solved_at_end

    # KV (labels 370–380): problem changes, periods 2..NTP.
    kv = int((kcbc[1:] != kcbc[:-1]).sum())

    styles = [o.style for o in history.outcomes if o.style is not None]
    return SummaryStatistics(
        choices_not_made=kz,
        choice_persistence=ky,
        dm_velocity=kx,
        problems_not_solved=kw,
        problem_velocity=kv,
        problem_latency=ku,
        problem_persistence=kt,
        dm_inactivity=dm_resting,
        energy_reserve=float(energy_reserve),
        energy_wastage=float(energy_wastage),
        choices_made=len(styles),
        by_resolution=sum(s is DecisionStyle.RESOLUTION for s in styles),
        by_oversight=sum(s is DecisionStyle.OVERSIGHT for s in styles),
        by_flight=sum(s is DecisionStyle.FLIGHT for s in styles),
    )


def format_histories(history: FortranHistory) -> str:
    """Render the three history tables the program prints under ``IO = 2``."""
    lines = []
    ntp, nch = history.choices.shape
    ndm = history.decision_makers.shape[1]
    npr = history.problems.shape[1]
    lines.append("CHOICE ACTIVATION HISTORY (0=inactive, 1=active, 2=made)")
    lines.append("     " + " ".join(f"{i + 1:3d}" for i in range(nch)))
    for t in range(ntp):
        lines.append(f"{t + 1:3d}  " + " ".join(f"{v:3d}" for v in history.choices[t]))
    lines.append("")
    lines.append("DECISION MAKER ACTIVITY HISTORY (0=inactive, X=working on choice X)")
    lines.append("     " + " ".join(f"{k + 1:3d}" for k in range(ndm)))
    for t in range(ntp):
        lines.append(f"{t + 1:3d}  " + " ".join(f"{v:3d}" for v in history.decision_makers[t]))
    lines.append("")
    lines.append(
        "PROBLEM HISTORY (-1=not entered, 0=unattached, X=attached to choice X, **=solved)"
    )
    lines.append("     " + " ".join(f"{j + 1:3d}" for j in range(npr)))
    for t in range(ntp):
        cells = [" **" if v == SOLVED_MARK else f"{v:3d}" for v in history.problems[t]]
        lines.append(f"{t + 1:3d}  " + " ".join(cells))
    return "\n".join(lines)


def style_table(history: FortranHistory) -> np.ndarray:
    """Per-choice array of (choice id 1-based, period made or 0, style code) for quick display."""
    rows = []
    for o in history.outcomes:
        rows.append((o.choice + 1, o.period_made or 0, (o.style.value if o.style else "not made")))
    return np.array(rows, dtype=object)
