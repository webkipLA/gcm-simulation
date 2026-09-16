"""Extension points of the NetLogo garbage can model.

In Fioretti & Lomi's agent-based version, "organizational structure" is not a matrix but a set of
*movement constraints*: a participant may not step onto a patch holding an opportunity it is not
entitled to, and an opportunity may not step onto a patch holding participants (solutions,
problems) it may not meet. Everything else (the random walk, the meeting rule, the resolution
inequality, flights) is structure-free. The protocols below isolate exactly those pieces:

===================================  ==============================  ===============================
NetLogo                              Protocol                        Rule-based defaults
===================================  ==============================  ===============================
``decision-structure`` chooser       :class:`DecisionStructure`      ``structures.decision_structure``
``availability-structure`` chooser   :class:`AvailabilityStructure`  ``structures.availability_structure``
``access-structure`` chooser         :class:`AccessStructure`        ``structures.access_structure``
resolution inequality (eq. 5)        :class:`ResolutionRule`         ``rules.SumAbilityTimesBestEfficiency``
``postpone`` / ``pass-the-buck``     :class:`FlightSelector`         ``rules.MostDifficultToLatestArrival``
===================================  ==============================  ===============================

All ``*_may_enter`` methods answer the question "may this agent step onto ``target``?" and receive
the agents currently on the target patch plus the model (for parameters, the hierarchy divide and
the tick counter). They are called for every attempted move, so an implementation that consults
an external decision maker (e.g. an LLM) should cache aggressively or decide at a coarser level
(per agent per tick, per agent–opportunity pair, …) and merely look the decision up here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from gcm.netlogo.agents import Opportunity, Participant, PatchAgents, Problem, Solution

if TYPE_CHECKING:  # pragma: no cover
    from gcm.netlogo.model import GarbageCanABM


@runtime_checkable
class DecisionStructure(Protocol):
    """Who may make use of which choice opportunities (participants ↔ opportunities)."""

    name: str

    def participant_may_enter(
        self, participant: Participant, target: PatchAgents, model: GarbageCanABM
    ) -> bool: ...

    def opportunity_may_enter(
        self, opportunity: Opportunity, target: PatchAgents, model: GarbageCanABM
    ) -> bool: ...


@runtime_checkable
class AvailabilityStructure(Protocol):
    """Which solutions are available to which opportunities (solutions ↔ opportunities)."""

    name: str

    def solution_may_enter(
        self, solution: Solution, target: PatchAgents, model: GarbageCanABM
    ) -> bool: ...

    def opportunity_may_enter(
        self, opportunity: Opportunity, target: PatchAgents, model: GarbageCanABM
    ) -> bool: ...


@runtime_checkable
class AccessStructure(Protocol):
    """Which problems reach which opportunities (problems ↔ opportunities)."""

    name: str

    def problem_may_enter(
        self, problem: Problem, target: PatchAgents, model: GarbageCanABM
    ) -> bool: ...

    def opportunity_may_enter(
        self, opportunity: Opportunity, target: PatchAgents, model: GarbageCanABM
    ) -> bool: ...


@runtime_checkable
class ResolutionRule(Protocol):
    """Given the agents on a patch that holds at least one participant, opportunity, solution
    and problem: is a decision by resolution made?"""

    name: str

    def resolves(self, here: PatchAgents, model: GarbageCanABM) -> bool: ...


@runtime_checkable
class FlightSelector(Protocol):
    """Which problem leaves a blocked decision process, and with whom."""

    name: str

    def postponement(
        self, here: PatchAgents, model: GarbageCanABM
    ) -> tuple[Problem, Opportunity]: ...

    def buck_passing(
        self, here: PatchAgents, model: GarbageCanABM
    ) -> tuple[Problem, Participant]: ...
