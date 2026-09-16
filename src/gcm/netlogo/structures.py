"""Rule-based organizational structures of the NetLogo model (movement constraints).

Ports of ``opportunity-can-move``, ``participant-can-move``, ``solution-can-move`` and
``problem-can-move``. Each structure chooser constrains two kinds of movement:

* an agent (participant / solution / problem) may not step onto a patch holding an opportunity of
  the wrong importance class for its attribute class;
* an opportunity may not step onto a patch holding an agent of the wrong attribute class for its
  importance class.

Classes are cut at ``(max − min) / 2`` (see :class:`gcm.netlogo.parameters.NetLogoParameters`).
The two comparisons are not perfectly symmetric in the original code: an agent is "high" iff
``value > threshold``, whereas an opportunity is barred from "low" agents with ``value <
threshold`` and from "high" agents with ``value > threshold``, and this is reproduced literally.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gcm.netlogo.agents import Agent, Opportunity, Participant, PatchAgents, Problem, Solution
from gcm.netlogo.parameters import NetLogoParameters, Structure

if TYPE_CHECKING:  # pragma: no cover
    from gcm.netlogo.model import GarbageCanABM


@dataclass
class _HierarchyRule:
    """Shared logic of the three structure dimensions."""

    structure: Structure
    attribute: str  # "ability" | "efficiency" | "difficulty"
    threshold_of: Callable[[NetLogoParameters], float]
    agents_of: Callable[[PatchAgents], list]  # which breed list on the target patch to inspect
    name: str = ""

    def __post_init__(self) -> None:
        self.name = f"{self.structure.value} ({self.attribute})"

    # -- agent → opportunity ------------------------------------------------------------------
    def agent_may_enter(self, agent: Agent, target: PatchAgents, model: GarbageCanABM) -> bool:
        if self.structure is Structure.ORGANIZED_ANARCHY or not target.opportunities:
            return True
        high = getattr(agent, self.attribute) > self.threshold_of(model.params)
        divide = model.hierarchy_divide
        if self.structure is Structure.COMPETENT_HIERARCHY:
            # high agents may not approach unimportant opportunities; low agents not important ones
            barred = (lambda o: o.who > divide) if high else (lambda o: o.who <= divide)
        else:  # incompetent hierarchy: the reverse
            barred = (lambda o: o.who <= divide) if high else (lambda o: o.who > divide)
        return not any(barred(o) for o in target.opportunities)

    # -- opportunity → agents ----------------------------------------------------------------
    def opportunity_may_enter(
        self, opportunity: Opportunity, target: PatchAgents, model: GarbageCanABM
    ) -> bool:
        if self.structure is Structure.ORGANIZED_ANARCHY:
            return True
        agents = self.agents_of(target)
        if not agents:
            return True
        thr = self.threshold_of(model.params)
        important = opportunity.who <= model.hierarchy_divide
        attr = self.attribute
        if self.structure is Structure.COMPETENT_HIERARCHY:
            # important opportunities avoid low agents; unimportant ones avoid high agents
            if important:
                return not any(getattr(a, attr) < thr for a in agents)
            return not any(getattr(a, attr) > thr for a in agents)
        # incompetent hierarchy: important opportunities avoid high agents, unimportant avoid low
        if important:
            return not any(getattr(a, attr) > thr for a in agents)
        return not any(getattr(a, attr) < thr for a in agents)


class DecisionStructureRule(_HierarchyRule):
    """``decision-structure``: participants ↔ opportunities, classed by *ability*."""

    def __init__(self, structure: Structure) -> None:
        super().__init__(
            structure, "ability", lambda p: p.ability_threshold, lambda t: t.participants
        )

    def participant_may_enter(
        self, participant: Participant, target: PatchAgents, model: GarbageCanABM
    ) -> bool:
        return self.agent_may_enter(participant, target, model)


class AvailabilityStructureRule(_HierarchyRule):
    """``availability-structure``: solutions ↔ opportunities, classed by *efficiency*."""

    def __init__(self, structure: Structure) -> None:
        super().__init__(
            structure, "efficiency", lambda p: p.efficiency_threshold, lambda t: t.solutions
        )

    def solution_may_enter(
        self, solution: Solution, target: PatchAgents, model: GarbageCanABM
    ) -> bool:
        return self.agent_may_enter(solution, target, model)


class AccessStructureRule(_HierarchyRule):
    """``access-structure``: problems ↔ opportunities, classed by *difficulty*."""

    def __init__(self, structure: Structure) -> None:
        super().__init__(
            structure, "difficulty", lambda p: p.difficulty_threshold, lambda t: t.problems
        )

    def problem_may_enter(
        self, problem: Problem, target: PatchAgents, model: GarbageCanABM
    ) -> bool:
        return self.agent_may_enter(problem, target, model)


def decision_structure(structure: Structure) -> DecisionStructureRule:
    return DecisionStructureRule(structure)


def availability_structure(structure: Structure) -> AvailabilityStructureRule:
    return AvailabilityStructureRule(structure)


def access_structure(structure: Structure) -> AccessStructureRule:
    return AccessStructureRule(structure)
