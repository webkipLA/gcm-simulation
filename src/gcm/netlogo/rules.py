"""Rule-based defaults for the decision rule and the flight selection of the NetLogo model."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeVar

from gcm.netlogo.agents import Opportunity, Participant, PatchAgents, Problem

if TYPE_CHECKING:  # pragma: no cover
    from gcm.netlogo.model import GarbageCanABM

T = TypeVar("T")


def max_one_of(agents: Sequence[T], key, rng) -> T:
    """NetLogo ``max-one-of``: the agent with the highest key; ties are broken at random."""
    best = max(key(a) for a in agents)
    tied = [a for a in agents if key(a) == best]
    return tied[0] if len(tied) == 1 else rng.choice(tied)


class SumAbilityTimesBestEfficiency:
    """Resolution inequality of Fioretti & Lomi (2008, eq. 5) as implemented in NetLogo:

    ``sum(ability of participants here) × efficiency of the most efficient solution here
    ≥ sum(difficulty of problems here)``.
    """

    name = "sum_ability_x_best_efficiency"

    def resolves(self, here: PatchAgents, model: GarbageCanABM) -> bool:
        ability = sum(p.ability for p in here.participants)
        efficiency = max(s.efficiency for s in here.solutions)
        difficulty = sum(p.difficulty for p in here.problems)
        return ability * efficiency >= difficulty


class MostDifficultToLatestArrival:
    """Flight selection of ``to postpone`` / ``to pass-the-buck``: the most difficult problem on
    the patch is coupled to the opportunity (participant) that arrived most recently
    (``max-one-of … [last-movement]``)."""

    name = "most_difficult_to_latest_arrival"

    def postponement(self, here: PatchAgents, model: GarbageCanABM) -> tuple[Problem, Opportunity]:
        rng = model.rng
        problem = max_one_of(here.problems, lambda p: p.difficulty, rng)
        opportunity = max_one_of(here.opportunities, lambda o: o.last_movement, rng)
        return problem, opportunity

    def buck_passing(self, here: PatchAgents, model: GarbageCanABM) -> tuple[Problem, Participant]:
        rng = model.rng
        problem = max_one_of(here.problems, lambda p: p.difficulty, rng)
        participant = max_one_of(here.participants, lambda a: a.last_movement, rng)
        return problem, participant
