"""The agent-based garbage can model, a port of ``GarbageCan_simplified17.nlogox`` (NetLogo 7.0.4).

Structure of one tick (``to go``)::

    tick                       → self.ticks += 1
    decision-making            → _decision_making()   (per patch, random order)
    move                       → _move()              (flying pairs first, then free agents)
    monitor                    → _monitor()

Everything that the NetLogo program treats as state is state here too, including patch colours
(``white`` = blocked process, ``brown`` = flying pair, ``black`` = free; ``free-spot`` only accepts
black, empty patches) and ``pcolor-white-since``.

Two NetLogo idioms that affect the dynamics are reproduced deliberately:

* ``ask patches [ ask <breed>-here … ]`` re-evaluates ``-here`` per patch, so an agent that moves
  onto a patch that has not yet been processed in this tick is asked again there. Flying pairs
  therefore travel about e − 1 ≈ 1.7 patches per tick on average. This is emulated exactly by
  processing patches in a random order and re-queuing the destination patch when it is later in
  that order.
* ``max-one-of`` / ``one-of`` break ties at random.

Randomness comes from one :class:`random.Random` instance seeded from the parameters.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field, replace

from gcm.netlogo import rules, structures
from gcm.netlogo.agents import (
    Opportunity,
    Participant,
    PatchAgents,
    PatchColor,
    Problem,
    Solution,
)
from gcm.netlogo.hierarchy import hierarchy_divide
from gcm.netlogo.interfaces import (
    AccessStructure,
    AvailabilityStructure,
    DecisionStructure,
    FlightSelector,
    ResolutionRule,
)
from gcm.netlogo.parameters import NetLogoParameters

# heading index → (dx, dy); NetLogo heading 0 = north (y + 1), 90 = east (x + 1)
_DIRECTIONS = ((0, 1), (1, 0), (0, -1), (-1, 0))
_EMPTY = PatchAgents()


@dataclass
class NetLogoComponents:
    """The pluggable behavioural components of one run (see :mod:`gcm.netlogo.interfaces`)."""

    decision_structure: DecisionStructure
    availability_structure: AvailabilityStructure
    access_structure: AccessStructure
    resolution_rule: ResolutionRule = field(default_factory=rules.SumAbilityTimesBestEfficiency)
    flight_selector: FlightSelector = field(default_factory=rules.MostDifficultToLatestArrival)

    @classmethod
    def classic(cls, params: NetLogoParameters) -> NetLogoComponents:
        """The rule-based components selected by the three structure choosers."""
        return cls(
            decision_structure=structures.decision_structure(params.decision_structure),
            availability_structure=structures.availability_structure(params.availability_structure),
            access_structure=structures.access_structure(params.access_structure),
        )


@dataclass
class Event:
    """One decision or flight (the information ``show-details?`` prints to the command center)."""

    tick: int
    kind: str  # "resolution" | "oversight" | "postponement" | "buck-passing"
    x: int
    y: int
    opportunity: int  # who of the opportunity involved (for decisions: the one sampled for the
    # high/low counters; for postponements: the opportunity that leaves)
    n_participants: int
    n_problems: int
    after_block: bool = False  # decision on a patch that was blocked (white) before


@dataclass
class NetLogoResults:
    """The globals reported by the BehaviorSpace experiments plus a few derived indicators."""

    ticks: int
    num_oversights: int
    num_resolutions: int
    num_blocked_oversights: int
    num_blocked_resolutions: int
    num_postponements: int
    num_buck_passings: int
    ave_duration_blocked: float
    ave_duration_postponed: float
    ave_duration_passed: float
    num_oversights_high: int | None
    num_oversights_low: int | None
    num_resolutions_high: int | None
    num_resolutions_low: int | None
    currently_blocked: int
    currently_postponed: int
    currently_passed: int

    @property
    def decisions(self) -> int:
        return self.num_oversights + self.num_resolutions

    @property
    def share_resolutions(self) -> float:
        """Resolutions / all decisions (Fioretti & Lomi's efficiency indicator)."""
        return self.num_resolutions / self.decisions if self.decisions else float("nan")

    @property
    def share_oversights(self) -> float:
        return self.num_oversights / self.decisions if self.decisions else float("nan")

    @property
    def flights(self) -> int:
        return self.num_postponements + self.num_buck_passings

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d.update(
            decisions=self.decisions,
            share_resolutions=self.share_resolutions,
            share_oversights=self.share_oversights,
            flights=self.flights,
        )
        return d


class GarbageCanABM:
    """One run of the NetLogo garbage can model."""

    def __init__(
        self,
        params: NetLogoParameters | None = None,
        components: NetLogoComponents | None = None,
        record_events: bool = True,
        record_every: int = 0,
    ) -> None:
        self.params = params or NetLogoParameters()
        self.components = components or NetLogoComponents.classic(self.params)
        self.record_events = record_events
        self.record_every = record_every
        self.rng = random.Random(self.params.seed)
        self.setup()

    # =====================================================================================
    # setup
    # =====================================================================================
    def setup(self) -> None:
        """``to setup``: create the agents and reset all counters."""
        p, rng = self.params, self.rng
        self.ticks = 0
        self.width, self.height = p.world_width, p.world_height
        self.n_patches = self.width * self.height

        # cumulative counters (globals)
        self.num_oversights = 0
        self.num_blocked_oversights = 0
        self.num_resolutions = 0
        self.num_blocked_resolutions = 0
        self.num_postponements = 0
        self.num_buck_passings = 0
        self.num_blocked = 0
        self.duration_blocked = 0.0
        self.ave_duration_blocked = 0.0
        self.num_postponed = 0
        self.duration_postponed = 0.0
        self.ave_duration_postponed = 0.0
        self.num_passed = 0
        self.duration_passed = 0.0
        self.ave_duration_passed = 0.0
        self.num_oversights_high = 0
        self.num_oversights_low = 0
        self.num_resolutions_high = 0
        self.num_resolutions_low = 0

        # patch state: only non-black patches / occupied patches are stored
        self.color: dict[int, PatchColor] = {}
        self.white_since: dict[int, int] = {}
        self.here: dict[int, PatchAgents] = {}

        # agents: creation order fixes the who numbers exactly as in the .nlogox
        who = 0
        self.opportunities: list[Opportunity] = []
        for _ in range(p.number_of_opportunities):
            a = Opportunity(who, rng.randrange(self.width), rng.randrange(self.height))
            self.opportunities.append(a)
            self._add(a)
            who += 1
        self.participants: list[Participant] = []
        for _ in range(p.number_of_participants):
            a = Participant(
                who,
                rng.randrange(self.width),
                rng.randrange(self.height),
                ability=rng.random() * (p.max_ability - p.min_ability) + p.min_ability,
            )
            self.participants.append(a)
            self._add(a)
            who += 1
        self.solutions: list[Solution] = []
        for _ in range(p.number_of_solutions):
            a = Solution(
                who,
                rng.randrange(self.width),
                rng.randrange(self.height),
                efficiency=rng.random() * (p.max_efficiency - p.min_efficiency) + p.min_efficiency,
            )
            self.solutions.append(a)
            self._add(a)
            who += 1
        self.problems: list[Problem] = []
        for _ in range(p.number_of_problems):
            a = Problem(
                who,
                rng.randrange(self.width),
                rng.randrange(self.height),
                difficulty=rng.random() * (p.max_difficulty - p.min_difficulty) + p.min_difficulty,
            )
            self.problems.append(a)
            self._add(a)
            who += 1

        self.hierarchy_active = p.hierarchy_active
        self.hierarchy_divide = (
            hierarchy_divide(p.number_of_opportunities, p.span_of_control)
            if self.hierarchy_active
            else -1
        )
        self.events: list[Event] = []
        self.timeline: list[dict] = []
        # diagnostics for the NetLogo re-ask idiom (see _move_flying_pairs)
        self.stats_flying_opportunity_ticks = 0
        self.stats_flying_opportunity_moves = 0

    # =====================================================================================
    # occupancy helpers
    # =====================================================================================
    def _index(self, x: int, y: int) -> int:
        return y * self.width + x

    def _list_for(self, here: PatchAgents, agent) -> list:
        if isinstance(agent, Opportunity):
            return here.opportunities
        if isinstance(agent, Participant):
            return here.participants
        if isinstance(agent, Solution):
            return here.solutions
        return here.problems

    def _add(self, agent) -> None:
        idx = self._index(agent.x, agent.y)
        here = self.here.get(idx)
        if here is None:
            here = self.here[idx] = PatchAgents()
        self._list_for(here, agent).append(agent)

    def _remove(self, agent) -> None:
        idx = self._index(agent.x, agent.y)
        here = self.here[idx]
        self._list_for(here, agent).remove(agent)
        if here.is_empty():
            del self.here[idx]

    def _move_to(self, agent, x: int, y: int) -> int:
        """``move-to``: relocate ``agent`` to patch (x, y); returns the new patch index."""
        self._remove(agent)
        agent.x, agent.y = x, y
        self._add(agent)
        return self._index(x, y)

    def _ahead(self, agent, heading: int) -> tuple[int, int]:
        """``patch-ahead 1`` on the torus."""
        dx, dy = _DIRECTIONS[heading]
        return (agent.x + dx) % self.width, (agent.y + dy) % self.height

    def agents_at(self, x: int, y: int) -> PatchAgents:
        return self.here.get(self._index(x, y), _EMPTY)

    def color_at(self, idx: int) -> PatchColor:
        return self.color.get(idx, PatchColor.BLACK)

    def _set_color(self, idx: int, color: PatchColor) -> None:
        if color is PatchColor.BLACK:
            self.color.pop(idx, None)
        else:
            self.color[idx] = color

    def is_important(self, opportunity: Opportunity) -> bool:
        """High-importance opportunity (``who <= hierarchy-divide``)."""
        return opportunity.who <= self.hierarchy_divide

    # =====================================================================================
    # movement permissions (the four ``…-can-move`` reporters)
    # =====================================================================================
    def opportunity_can_move(self, o: Opportunity, target: PatchAgents) -> bool:
        c = self.components
        return (
            c.decision_structure.opportunity_may_enter(o, target, self)
            and c.availability_structure.opportunity_may_enter(o, target, self)
            and c.access_structure.opportunity_may_enter(o, target, self)
        )

    def participant_can_move(self, a: Participant, target: PatchAgents) -> bool:
        return self.components.decision_structure.participant_may_enter(a, target, self)

    def solution_can_move(self, s: Solution, target: PatchAgents) -> bool:
        return self.components.availability_structure.solution_may_enter(s, target, self)

    def problem_can_move(self, pr: Problem, target: PatchAgents) -> bool:
        return self.components.access_structure.problem_may_enter(pr, target, self)

    # =====================================================================================
    # go
    # =====================================================================================
    def go(self) -> None:
        """One tick: ``tick``, ``decision-making``, ``move``, ``monitor``."""
        self.ticks += 1
        self._decision_making()
        self._move()
        self._monitor()
        if self.record_every and self.ticks % self.record_every == 0:
            self.timeline.append(self.results().as_dict())

    def run(self, ticks: int | None = None) -> NetLogoResults:
        """Run ``ticks`` ticks (default: the ``stop-at`` parameter) and return the results."""
        n = self.params.stop_at if ticks is None else ticks
        for _ in range(n):
            self.go()
        return self.results()

    # -------------------------------------------------------------------------------------
    def _decision_making(self) -> None:
        rng = self.rng
        patches = list(self.here.keys() | self.color.keys())
        rng.shuffle(patches)
        for idx in patches:
            here = self.here.get(idx)
            # Reset colours: brown under flying pairs, otherwise black unless blocked (white).
            if here is not None and any(pr.postponed or pr.passed for pr in here.problems):
                self.color[idx] = PatchColor.BROWN
            elif self.color.get(idx) is not PatchColor.WHITE:
                self.color.pop(idx, None)
            if here is None or not (here.participants and here.opportunities and here.solutions):
                continue
            # Agents paired because of a flight enter the decision process on equal status.
            for a in here.participants:
                if a.charged:
                    a.charged = False
                    a.with_problem = None
            for o in here.opportunities:
                if o.charged:
                    o.charged = False
                    o.with_problem = None
            for pr in here.problems:
                if pr.postponed:
                    pr.postponed = False
                    pr.to_opportunity = None
                if pr.passed:
                    pr.passed = False
                    pr.to_participant = None
            if here.problems:
                if self.components.resolution_rule.resolves(here, self):
                    self._resolution(idx, here)
                else:
                    self._blocked(idx, here)
            else:
                self._oversight(idx, here)

    def _resolution(self, idx: int, here: PatchAgents) -> None:
        was_white = self.color.get(idx) is PatchColor.WHITE
        self.num_resolutions += 1
        if was_white:
            self.num_blocked_resolutions += 1
        self.color[idx] = PatchColor.LIME
        self.white_since[idx] = 0
        for pr in here.problems:
            pr.since = 0
        opp = self.rng.choice(here.opportunities)
        if self.hierarchy_active:
            if self.is_important(opp):
                self.num_resolutions_high += 1
            else:
                self.num_resolutions_low += 1
        for a in here.all():
            a.blocked = False
        if self.record_events:
            self.events.append(
                Event(
                    self.ticks,
                    "resolution",
                    idx % self.width,
                    idx // self.width,
                    opp.who,
                    len(here.participants),
                    len(here.problems),
                    was_white,
                )
            )

    def _oversight(self, idx: int, here: PatchAgents) -> None:
        was_white = self.color.get(idx) is PatchColor.WHITE
        self.num_oversights += 1
        if was_white:
            self.num_blocked_oversights += 1
        self.color[idx] = PatchColor.SKY
        self.white_since[idx] = 0
        opp = self.rng.choice(here.opportunities)  # chosenOppOve
        if self.hierarchy_active:
            if self.is_important(opp):
                self.num_oversights_high += 1
            else:
                self.num_oversights_low += 1
        for a in here.all():
            a.blocked = False
        if self.record_events:
            self.events.append(
                Event(
                    self.ticks,
                    "oversight",
                    idx % self.width,
                    idx // self.width,
                    opp.who,
                    len(here.participants),
                    0,
                    was_white,
                )
            )

    def _blocked(self, idx: int, here: PatchAgents) -> None:
        rng, ticks, p = self.rng, self.ticks, self.params
        for a in here.participants:
            a.blocked = True
        if not any(o.blocked for o in here.opportunities):
            rng.choice(here.opportunities).blocked = True
        if not any(s.blocked for s in here.solutions):
            rules.max_one_of(here.solutions, lambda s: s.efficiency, rng).blocked = True
        for pr in here.problems:
            pr.blocked = True
        if self.color.get(idx) is not PatchColor.WHITE:
            self.color[idx] = PatchColor.WHITE
            self.white_since[idx] = ticks

        # FLIGHTS: the three sequential ``if`` blocks of the original, re-evaluated in turn.
        def recent_opportunity() -> bool:
            ws = self.white_since.get(idx, 0)
            return any(o.last_movement == ticks - 1 and ticks > ws for o in here.opportunities)

        def recent_participant() -> bool:
            ws = self.white_since.get(idx, 0)
            return any(a.last_movement == ticks - 1 and ticks > ws for a in here.participants)

        if (
            p.postpone
            and len(here.opportunities) > 1
            and recent_opportunity()
            and (not p.buckpass or not recent_participant())
        ):
            self._postpone(idx, here)
        if (
            p.buckpass
            and len(here.participants) > 1
            and recent_participant()
            and (not p.postpone or not recent_opportunity())
        ):
            self._pass_the_buck(idx, here)
        if (
            p.postpone
            and len(here.opportunities) > 1
            and recent_opportunity()
            and p.buckpass
            and len(here.participants) > 1
            and recent_participant()
        ):
            if rng.randrange(2) == 0:
                self._postpone(idx, here)
            else:
                self._pass_the_buck(idx, here)

    # -------------------------------------------------------------------------------------
    def _free_spot(self) -> tuple[int, int]:
        """``free-spot``: a random black patch with no agents on it."""
        rng = self.rng
        while True:
            x, y = rng.randrange(self.width), rng.randrange(self.height)
            idx = self._index(x, y)
            if idx not in self.color and idx not in self.here:
                return x, y

    def _postpone(self, idx: int, here: PatchAgents) -> None:
        problem, opportunity = self.components.flight_selector.postponement(here, self)
        opportunity.blocked = False
        opportunity.charged = True
        opportunity.with_problem = problem
        x, y = self._free_spot()
        self._move_to(opportunity, x, y)
        problem.blocked = False
        problem.postponed = True
        problem.to_opportunity = opportunity
        problem.since = self.ticks
        self._move_to(problem, opportunity.x, opportunity.y)
        self.num_postponements += 1
        if self.record_events:
            self.events.append(
                Event(
                    self.ticks,
                    "postponement",
                    idx % self.width,
                    idx // self.width,
                    opportunity.who,
                    len(here.participants),
                    len(here.problems) + 1,
                    True,
                )
            )

    def _pass_the_buck(self, idx: int, here: PatchAgents) -> None:
        problem, participant = self.components.flight_selector.buck_passing(here, self)
        participant.blocked = False
        participant.charged = True
        participant.with_problem = problem
        x, y = self._free_spot()
        self._move_to(participant, x, y)
        problem.blocked = False
        problem.passed = True
        problem.to_participant = participant
        problem.since = self.ticks
        self._move_to(problem, participant.x, participant.y)
        self.num_buck_passings += 1
        if self.record_events:
            opp = here.opportunities[0].who if here.opportunities else -1
            self.events.append(
                Event(
                    self.ticks,
                    "buck-passing",
                    idx % self.width,
                    idx // self.width,
                    opp,
                    len(here.participants) + 1,
                    len(here.problems) + 1,
                    True,
                )
            )

    # =====================================================================================
    # move
    # =====================================================================================
    def _move(self) -> None:
        self._move_flying_pairs()
        rng, ticks = self.rng, self.ticks

        # Free agents: one ``ask <breed> with […]`` per breed, each agent asked once, random order.
        opps = [o for o in self.opportunities if not o.blocked and not o.charged]
        rng.shuffle(opps)
        for o in opps:
            x, y = self._ahead(o, rng.randrange(4))
            if self.opportunity_can_move(o, self.agents_at(x, y)):
                self._move_to(o, x, y)
                o.last_movement = ticks

        parts = [a for a in self.participants if not a.blocked and not a.charged]
        rng.shuffle(parts)
        for a in parts:
            x, y = self._ahead(a, rng.randrange(4))
            if self.participant_can_move(a, self.agents_at(x, y)):
                self._move_to(a, x, y)
                a.last_movement = ticks

        sols = [s for s in self.solutions if not s.blocked]
        rng.shuffle(sols)
        for s in sols:
            x, y = self._ahead(s, rng.randrange(4))
            if self.solution_can_move(s, self.agents_at(x, y)):
                self._move_to(s, x, y)

        probs = [
            pr for pr in self.problems if not pr.blocked and not pr.postponed and not pr.passed
        ]
        rng.shuffle(probs)
        for pr in probs:
            x, y = self._ahead(pr, rng.randrange(4))
            if self.problem_can_move(pr, self.agents_at(x, y)):
                self._move_to(pr, x, y)

    def _move_flying_pairs(self) -> None:
        """``ask patches [ … ]`` part of ``to move``: flying couples move first.

        Patches are visited in a random order; an agent that lands on a patch that comes later
        in that order is asked again when that patch is visited (NetLogo semantics).
        """
        rng, ticks = self.rng, self.ticks
        rank: dict[int, float] = {}

        def rank_of(idx: int) -> float:
            r = rank.get(idx)
            if r is None:
                r = rank[idx] = rng.random()
            return r

        heap: list[tuple[float, int]] = []
        queued: set[int] = set()
        for o in self.opportunities:
            if o.charged and not o.blocked:
                self.stats_flying_opportunity_ticks += 1
                idx = self._index(o.x, o.y)
                if idx not in queued:
                    queued.add(idx)
                    heapq.heappush(heap, (rank_of(idx), idx))
        for a in self.participants:
            if a.charged and not a.blocked:
                idx = self._index(a.x, a.y)
                if idx not in queued:
                    queued.add(idx)
                    heapq.heappush(heap, (rank_of(idx), idx))
        for pr in self.problems:
            if not pr.blocked and (
                (pr.postponed and pr.to_opportunity is not None)
                or (pr.passed and pr.to_participant is not None)
            ):
                idx = self._index(pr.x, pr.y)
                if idx not in queued:
                    queued.add(idx)
                    heapq.heappush(heap, (rank_of(idx), idx))

        done: set[int] = set()

        def requeue(new_idx: int, current_rank: float) -> None:
            if new_idx in done or new_idx in queued:
                return
            r = rank_of(new_idx)
            if r > current_rank:
                queued.add(new_idx)
                heapq.heappush(heap, (r, new_idx))

        while heap:
            r, idx = heapq.heappop(heap)
            queued.discard(idx)
            if idx in done:
                continue
            done.add(idx)
            here = self.here.get(idx)
            if here is None:
                continue

            # Paired problems and opportunities move together (opportunities move unconditionally).
            flying = [o for o in here.opportunities if not o.blocked and o.charged]
            rng.shuffle(flying)
            for o in flying:
                heading = rng.randrange(4)
                if self.color.get(idx) is PatchColor.BROWN:
                    self.color.pop(idx, None)
                x, y = self._ahead(o, heading)
                new_idx = self._move_to(o, x, y)
                o.last_movement = ticks
                self.color[new_idx] = PatchColor.BROWN
                self.stats_flying_opportunity_moves += 1
                requeue(new_idx, r)
            following = [
                pr
                for pr in here.problems
                if not pr.blocked and pr.postponed and pr.to_opportunity is not None
            ]
            rng.shuffle(following)
            for pr in following:
                new_idx = self._move_to(pr, pr.to_opportunity.x, pr.to_opportunity.y)
                requeue(new_idx, r)

            # Paired problems and participants move together (participants obey the decision structure).
            flying_p = [a for a in here.participants if not a.blocked and a.charged]
            rng.shuffle(flying_p)
            for a in flying_p:
                initial = rng.randrange(4)
                heading = initial
                while True:
                    x, y = self._ahead(a, heading)
                    if self.participant_can_move(a, self.agents_at(x, y)):
                        if self.color.get(idx) is PatchColor.BROWN:
                            self.color.pop(idx, None)
                        new_idx = self._move_to(a, x, y)
                        a.last_movement = ticks
                        self.color[new_idx] = PatchColor.BROWN
                        requeue(new_idx, r)
                        break
                    heading = (heading + 1) % 4
                    if heading == initial:
                        break
            following_p = [
                pr
                for pr in here.problems
                if not pr.blocked and pr.passed and pr.to_participant is not None
            ]
            rng.shuffle(following_p)
            for pr in following_p:
                new_idx = self._move_to(pr, pr.to_participant.x, pr.to_participant.y)
                requeue(new_idx, r)

    # =====================================================================================
    # monitor
    # =====================================================================================
    def _monitor(self) -> None:
        ticks = self.ticks
        white = [idx for idx, c in self.color.items() if c is PatchColor.WHITE]
        if white:
            self.num_blocked += len(white)
            now = sum(ticks - self.white_since.get(idx, 0) for idx in white) / len(white)
            self.duration_blocked += now
            self.ave_duration_blocked = self.duration_blocked / self.num_blocked
        postponed = [pr for pr in self.problems if pr.postponed]
        if postponed:
            self.num_postponed += sum(1 for o in self.opportunities if o.charged)
            now = sum(ticks - pr.since for pr in postponed) / len(postponed)
            self.duration_postponed += now
            self.ave_duration_postponed = self.duration_postponed / self.num_postponed
        passed = [pr for pr in self.problems if pr.passed]
        if passed:
            self.num_passed += sum(1 for a in self.participants if a.charged)
            now = sum(ticks - pr.since for pr in passed) / len(passed)
            self.duration_passed += now
            self.ave_duration_passed = self.duration_passed / self.num_passed

    # =====================================================================================
    # reporting
    # =====================================================================================
    def results(self) -> NetLogoResults:
        h = self.hierarchy_active
        return NetLogoResults(
            ticks=self.ticks,
            num_oversights=self.num_oversights,
            num_resolutions=self.num_resolutions,
            num_blocked_oversights=self.num_blocked_oversights,
            num_blocked_resolutions=self.num_blocked_resolutions,
            num_postponements=self.num_postponements,
            num_buck_passings=self.num_buck_passings,
            ave_duration_blocked=self.ave_duration_blocked,
            ave_duration_postponed=self.ave_duration_postponed,
            ave_duration_passed=self.ave_duration_passed,
            num_oversights_high=self.num_oversights_high if h else None,
            num_oversights_low=self.num_oversights_low if h else None,
            num_resolutions_high=self.num_resolutions_high if h else None,
            num_resolutions_low=self.num_resolutions_low if h else None,
            currently_blocked=sum(1 for c in self.color.values() if c is PatchColor.WHITE),
            currently_postponed=sum(1 for o in self.opportunities if o.charged),
            currently_passed=sum(1 for a in self.participants if a.charged),
        )

    def snapshot(self) -> dict:
        """Positions and patch colours for plotting the world."""
        return {
            "ticks": self.ticks,
            "opportunities": [(o.x, o.y, o.who, o.blocked, o.charged) for o in self.opportunities],
            "participants": [
                (a.x, a.y, a.ability, a.blocked, a.charged) for a in self.participants
            ],
            "solutions": [(s.x, s.y, s.efficiency, s.blocked) for s in self.solutions],
            "problems": [
                (pr.x, pr.y, pr.difficulty, pr.blocked, pr.postponed or pr.passed)
                for pr in self.problems
            ],
            "colors": {idx: c.name.lower() for idx, c in self.color.items()},
            "width": self.width,
            "height": self.height,
        }

    def with_params(self, **changes) -> GarbageCanABM:
        """A fresh model with some parameters changed (convenience for the notebook)."""
        return GarbageCanABM(
            replace(self.params, **changes),
            record_events=self.record_events,
            record_every=self.record_every,
        )
