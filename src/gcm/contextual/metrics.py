"""Metrics per hierarchy level for both ports.

The existing summary statistics are aggregates over the whole organization. Research question 2
asks how decision styles, latencies and the problem resolution rate change *per hierarchy
level*, so this module adds the per-level view without touching the simulation cores.

FORTRAN
    The level of a choice or a problem is its importance rank (its index; 0 = most important).
    Ranks are grouped into ``n_levels`` equally sized groups, level 1 being the most important.
    Choice-level metrics come from the outcomes and the choice history, problem-level metrics
    from the problem history (``KCBC``).

NetLogo
    Opportunities carry their importance in ``who``; the level is the pyramid level of
    ``assign-importance`` (:func:`gcm.netlogo.hierarchy.level_of`) or the two-way split at the
    hierarchy divide. Decisions are attributed to the opportunity sampled for the high/low
    counters (the same one the NetLogo monitors use). The blocked duration before a decision is
    not part of the event log of the base model, so :class:`ObservedGarbageCanABM` records it;
    it changes nothing else and runs identically to the base class.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gcm.common import DecisionStyle
from gcm.fortran.model import FortranHistory
from gcm.fortran.state import ACTIVE, NOT_ENTERED_MARK, SOLVED_MARK
from gcm.netlogo.agents import PatchAgents, PatchColor
from gcm.netlogo.hierarchy import hierarchy_divide, level_of
from gcm.netlogo.model import Event, GarbageCanABM


def level_groups(n: int, n_levels: int) -> np.ndarray:
    """Level (1 = most important) of each of ``n`` ranks, in ``n_levels`` equal groups."""
    if not 1 <= n_levels <= n:
        raise ValueError("n_levels must be between 1 and the number of elements")
    return np.arange(n) * n_levels // n + 1


# ------------------------------------------------------------------------------------ FORTRAN
def fortran_level_metrics(history: FortranHistory, n_levels: int = 2) -> dict[str, float]:
    """Per-level metrics of one FORTRAN run as a flat dict (``<metric>_L<level>``).

    Choice levels (by choice rank): ``choices_made``, ``by_resolution``, ``by_oversight``,
    ``by_flight``, ``resolution_share`` (resolutions / choices made), ``decision_time``
    (periods a choice stayed active), ``problems_solved`` (at choices of that level).

    Problem levels (by problem rank): ``problems_solved_share``, ``problem_latency`` (periods
    entered but unattached, from period 2 as the program counts), ``problem_persistence``
    (periods attached), ``time_to_solution`` (periods from entry to solution, solved only).
    """
    n_choices, n_problems = history.choices.shape[1], history.problems.shape[1]
    choice_level = level_groups(n_choices, n_levels)
    problem_level = level_groups(n_problems, n_levels)
    out: dict[str, float] = {}
    active = history.choices == ACTIVE
    for level in range(1, n_levels + 1):
        choices = np.flatnonzero(choice_level == level)
        outcomes = [history.outcomes[i] for i in choices]
        made = [o for o in outcomes if o.style is not None]
        res = sum(o.style is DecisionStyle.RESOLUTION for o in made)
        out[f"choices_L{level}"] = len(choices)
        out[f"choices_made_L{level}"] = len(made)
        out[f"by_resolution_L{level}"] = res
        out[f"by_oversight_L{level}"] = sum(o.style is DecisionStyle.OVERSIGHT for o in made)
        out[f"by_flight_L{level}"] = sum(o.style is DecisionStyle.FLIGHT for o in made)
        out[f"resolution_share_L{level}"] = res / len(made) if made else float("nan")
        out[f"decision_time_L{level}"] = float(active[:, choices].sum())
        out[f"problems_solved_L{level}"] = sum(len(o.problems_solved) for o in made)

        problems = np.flatnonzero(problem_level == level)
        hist = history.problems[:, problems]
        later = hist[1:]
        solved = hist[-1] == SOLVED_MARK
        out[f"problems_L{level}"] = len(problems)
        out[f"problems_solved_share_L{level}"] = float(solved.mean())
        out[f"problem_latency_L{level}"] = float((later == 0).sum())
        out[f"problem_persistence_L{level}"] = float(
            ((later != 0) & (later != NOT_ENTERED_MARK) & (later != SOLVED_MARK)).sum()
        )
        times = []
        for j in range(hist.shape[1]):
            column = hist[:, j]
            entered = np.flatnonzero(column != NOT_ENTERED_MARK)
            done = np.flatnonzero(column == SOLVED_MARK)
            if len(entered) and len(done):
                times.append(int(done[0] - entered[0]) + 1)
        out[f"time_to_solution_L{level}"] = float(np.mean(times)) if times else float("nan")
    return out


# ------------------------------------------------------------------------------------ NetLogo
class ObservedGarbageCanABM(GarbageCanABM):
    """The NetLogo model with ``blocked_for`` recorded on every decision event.

    ``blocked_for`` is the number of ticks the patch had been blocked (white) when the decision
    was made, 0 for decisions on a free patch. Everything else is inherited unchanged.
    """

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("record_events", True)
        super().__init__(*args, **kwargs)
        self.blocked_for: dict[int, int] = {}  # event index → ticks blocked before the decision

    def _resolution(self, idx: int, here: PatchAgents) -> None:
        was_white = self.color.get(idx) is PatchColor.WHITE
        since = self.white_since.get(idx, 0)
        super()._resolution(idx, here)
        if self.record_events:
            self.blocked_for[len(self.events) - 1] = (self.ticks - since) if was_white else 0

    def _oversight(self, idx: int, here: PatchAgents) -> None:
        was_white = self.color.get(idx) is PatchColor.WHITE
        since = self.white_since.get(idx, 0)
        super()._oversight(idx, here)
        if self.record_events:
            self.blocked_for[len(self.events) - 1] = (self.ticks - since) if was_white else 0

    def event_frame(self, levels: str = "divide") -> pd.DataFrame:
        return event_frame(self, levels)


def event_frame(model: GarbageCanABM, levels: str = "divide") -> pd.DataFrame:
    """The event log as a table with the level of the opportunity involved.

    ``levels="divide"`` gives two levels (1 = high importance, ``who <= hierarchy_divide``),
    ``levels="pyramid"`` the pyramid level of ``assign-importance``. The divide is computed
    from the parameters, so it is available even when every structure chooser says
    "organized anarchy" and the model itself reports no high/low counters.
    """
    p = model.params
    divide = hierarchy_divide(p.number_of_opportunities, p.span_of_control)
    rows = []
    blocked_for = getattr(model, "blocked_for", {})
    for i, e in enumerate(model.events):
        row = dict(e.__dict__)
        if levels == "pyramid":
            row["level"] = (
                level_of(e.opportunity, p.span_of_control) if e.opportunity >= 0 else None
            )
        else:
            row["level"] = (1 if e.opportunity <= divide else 2) if e.opportunity >= 0 else None
        row["blocked_for"] = blocked_for.get(i)
        rows.append(row)
    columns = [*Event.__dataclass_fields__, "level", "blocked_for"]
    return pd.DataFrame(rows, columns=columns)


def netlogo_level_metrics(model: GarbageCanABM, levels: str = "divide") -> dict[str, float]:
    """Per-level metrics of one NetLogo run as a flat dict (``<metric>_L<level>``).

    ``resolutions``, ``oversights``, ``decisions``, ``resolution_share``, ``after_block``
    (decisions on a previously blocked patch), ``blocked_for`` (mean ticks blocked before such
    decisions; needs :class:`ObservedGarbageCanABM`), ``postponements`` (by the opportunity that
    leaves), ``buck_passings`` (by the first opportunity on the patch).
    """
    frame = event_frame(model, levels)
    out: dict[str, float] = {}
    if levels == "pyramid":
        p = model.params
        n_levels = level_of(p.number_of_opportunities - 1, p.span_of_control)
    else:
        n_levels = 2
    for level in range(1, n_levels + 1):
        here = frame[frame["level"] == level]
        res = int((here["kind"] == "resolution").sum())
        ove = int((here["kind"] == "oversight").sum())
        decisions = here[here["kind"].isin(["resolution", "oversight"])]
        blocked = decisions[decisions["after_block"]]
        out[f"resolutions_L{level}"] = res
        out[f"oversights_L{level}"] = ove
        out[f"decisions_L{level}"] = res + ove
        out[f"resolution_share_L{level}"] = res / (res + ove) if res + ove else float("nan")
        out[f"after_block_L{level}"] = len(blocked)
        durations = blocked["blocked_for"].dropna()
        out[f"blocked_for_L{level}"] = float(durations.mean()) if len(durations) else float("nan")
        out[f"postponements_L{level}"] = int((here["kind"] == "postponement").sum())
        out[f"buck_passings_L{level}"] = int((here["kind"] == "buck-passing").sum())
    return out


__all__ = [
    "ObservedGarbageCanABM",
    "event_frame",
    "fortran_level_metrics",
    "level_groups",
    "netlogo_level_metrics",
]
