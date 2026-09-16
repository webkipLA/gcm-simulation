"""The FORTRAN garbage can simulation, "version five" (Cohen, March & Olsen 1972, appendix).

One :class:`GarbageCanFortran` instance simulates one organizational variant under one entry-time
condition. The period loop follows the program's block structure:

1. activate choices / problems whose entry time is the current period (labels 101/110);
2. attach every active problem to a choice (labels 120–130), the *problem allocation rule*;
3. attach every decision maker to a choice (labels 140–150), the *energy allocation rule*;
4. recompute each active choice's requirement from attached problems and add this period's
   effective energy of attached decision makers to its cumulative energy (labels 160–199);
5. make every choice whose energy covers its requirement and solve the attached problems
   (labels 250–299), the *choice rule*;
6. record the histories ``KABC`` / ``KBBC`` / ``KCBC`` (labels 200–220).

The model is fully deterministic: the only exogenous randomness (entry orders) is fixed data.
All energy arithmetic goes through a pluggable backend (:mod:`gcm.fortran.arithmetic`) with the
same operand order as the FORTRAN statements, so that tie cases are decided the way the paper's
semantics (or, optionally, the original machine) decided them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from gcm.common import DecisionStyle, StructureKind
from gcm.fortran import allocation, structures
from gcm.fortran.arithmetic import get_arithmetic
from gcm.fortran.interfaces import (
    AccessStructure,
    ChoiceRule,
    DecisionMakerAllocationRule,
    DecisionStructure,
    EnergyDistribution,
    ProblemAllocationRule,
)
from gcm.fortran.parameters import FortranParameters, Load, MovementCondition
from gcm.fortran.state import (
    ACTIVE,
    INACTIVE,
    MADE,
    NOT_ATTACHED,
    NOT_ENTERED_MARK,
    SOLVED_MARK,
    FortranState,
)


@dataclass
class ChoiceOutcome:
    """How and when one choice was made (``None`` period = never made)."""

    choice: int
    period_made: int | None
    style: DecisionStyle | None
    problems_solved: tuple[int, ...] = ()


@dataclass
class FortranHistory:
    """Per-period histories in the encoding of the FORTRAN output tables.

    ``choices[t, i]``          : 0 inactive, 1 active, 2 made (``KABC``)
    ``decision_makers[t, k]``  : 0 idle, otherwise 1-based id of the choice attended (``KBBC``)
    ``problems[t, j]``         : -1 not entered, 0 unattached, 1-based choice id if attached,
                                 1000 solved (``KCBC``)
    Row ``t`` is period ``t + 1``. ``requirement`` / ``energy`` hold ``XERC`` / ``XEE`` per period.
    """

    choices: np.ndarray
    decision_makers: np.ndarray
    problems: np.ndarray
    outcomes: list[ChoiceOutcome]
    requirement: np.ndarray = field(default_factory=lambda: np.zeros(0))
    energy: np.ndarray = field(default_factory=lambda: np.zeros(0))


@dataclass
class FortranComponents:
    """The pluggable behavioural components of one run (see :mod:`gcm.fortran.interfaces`)."""

    decision_structure: DecisionStructure
    access_structure: AccessStructure
    energy_distribution: EnergyDistribution
    problem_allocation: ProblemAllocationRule = field(
        default_factory=allocation.ClosestToDecisionProblem
    )
    dm_allocation: DecisionMakerAllocationRule = field(
        default_factory=allocation.ClosestToDecisionDM
    )
    choice_rule: ChoiceRule = field(default_factory=allocation.EnergyAdditivityRule)

    @classmethod
    def classic(
        cls,
        access: StructureKind = StructureKind.UNSEGMENTED,
        decision: StructureKind = StructureKind.UNSEGMENTED,
        energy: int = structures.EnergyDistributionKind.EQUAL,
        params: FortranParameters | None = None,
    ) -> FortranComponents:
        """The rule-based components of the original program for a given structural variant."""
        p = params or FortranParameters()
        return cls(
            decision_structure=structures.decision_structure(
                decision, p.n_choices, p.n_decision_makers
            ),
            access_structure=structures.access_structure(access, p.n_problems, p.n_choices),
            energy_distribution=structures.energy_distribution(energy, p.n_decision_makers),
        )


class GarbageCanFortran:
    """One simulation run of the FORTRAN garbage can model."""

    def __init__(
        self,
        params: FortranParameters,
        load: Load,
        components: FortranComponents,
    ) -> None:
        self.params = params
        self.load = load
        self.components = components
        self.arith = get_arithmetic(params.arithmetic)
        self.state = FortranState(
            n_periods=params.n_periods,
            n_choices=params.n_choices,
            n_problems=params.n_problems,
            n_decision_makers=params.n_decision_makers,
            arith=self.arith,
        )
        self._initialise()

    # ------------------------------------------------------------------ setup ---------------
    def _initialise(self) -> None:
        s, p, a = self.state, self.params, self.arith
        nc, npb, nd, nt = p.n_choices, p.n_problems, p.n_decision_makers, p.n_periods
        s.choice_requirement = [
            a.const(p.initial_choice_requirement) for _ in range(nc)
        ]  # XERC = 1.1
        s.choice_energy = [a.zero() for _ in range(nc)]  # XEE = 0
        s.choice_status[:] = INACTIVE
        s.choice_ever_had_problems[:] = False
        s.dm_choice[:] = NOT_ATTACHED
        # XERP(J) = IL * 1.1  (integer IL converted to real, then multiplied)
        unit = a.const(p.problem_energy_unit)
        s.problem_requirement = [a.const(int(self.load) + 1) * unit for _ in range(npb)]
        s.problem_choice[:] = NOT_ATTACHED
        s.problem_status[:] = INACTIVE
        s.solution_coefficients = [a.const(repr(float(x))) for x in p.solution_coefficients]
        s.energy = self.components.energy_distribution.matrix(nd, nt, a)
        if len(s.energy) != nd or any(len(row) != nt for row in s.energy):
            raise ValueError(f"energy distribution must be {nd} × {nt}")
        s.energy_reserve = a.zero()
        s.energy_wastage = a.zero()
        s.dm_resting_periods = 0
        s.period = 0
        self._refresh_structures()

        self._h_choices = np.zeros((nt, nc), dtype=np.int64)
        self._h_dms = np.zeros((nt, nd), dtype=np.int64)
        self._h_problems = np.zeros((nt, npb), dtype=np.int64)
        self._h_req = np.zeros((nt, nc), dtype=np.float64)
        self._h_energy = np.zeros((nt, nc), dtype=np.float64)
        self._outcomes: dict[int, ChoiceOutcome] = {}
        self._dm_detach_flag = np.zeros(nd, dtype=bool)  # KDCW re-use for NA 3/4

    def _refresh_structures(self) -> None:
        s = self.state
        d = np.asarray(self.components.decision_structure.matrix(s), dtype=bool)
        a = np.asarray(self.components.access_structure.matrix(s), dtype=bool)
        if d.shape != (s.n_choices, s.n_decision_makers):
            raise ValueError(
                f"decision structure must have shape {(s.n_choices, s.n_decision_makers)}"
            )
        if a.shape != (s.n_problems, s.n_choices):
            raise ValueError(f"access structure must have shape {(s.n_problems, s.n_choices)}")
        s.decision_structure = d
        s.access_structure = a

    # ------------------------------------------------------------------ run -----------------
    def run(self) -> FortranHistory:
        """Simulate all periods and return the histories."""
        while self.state.period < self.params.n_periods:
            self.step()
        return self.history

    @property
    def history(self) -> FortranHistory:
        outcomes = [
            self._outcomes.get(i, ChoiceOutcome(choice=i, period_made=None, style=None))
            for i in range(self.params.n_choices)
        ]
        return FortranHistory(
            choices=self._h_choices.copy(),
            decision_makers=self._h_dms.copy(),
            problems=self._h_problems.copy(),
            outcomes=outcomes,
            requirement=self._h_req.copy(),
            energy=self._h_energy.copy(),
        )

    def step(self) -> None:
        """Advance one period (``LT``)."""
        s, p, c, a = self.state, self.params, self.components, self.arith
        if s.period >= p.n_periods:
            raise RuntimeError("simulation already finished")
        s.period += 1
        lt = s.period
        t = lt - 1  # 0-based row / column

        # Structures may change from period to period (dynamic / LLM-mediated variants).
        self._refresh_structures()

        # 1. Activation ---------------------------------------------------------------------
        s.choice_status[np.asarray(p.choice_entry_times) == lt] = ACTIVE
        s.problem_status[np.asarray(p.problem_entry_times) == lt] = ACTIVE

        # 2. Problem allocation (labels 120–130) ----------------------------------------------
        problems_move = p.movement in (MovementCondition.BOTH_MOVE, MovementCondition.PROBLEMS_ONLY)
        new_problem_choice = np.full(p.n_problems, NOT_ATTACHED, dtype=np.int64)  # JFF
        for j in range(p.n_problems):
            if s.problem_status[j] != ACTIVE:
                continue  # inactive / solved problems: JFF stays 0 → become unattached below
            if not problems_move and s.problem_choice[j] != NOT_ATTACHED:
                new_problem_choice[j] = s.problem_choice[j]  # label 127
            else:
                new_problem_choice[j] = c.problem_allocation.choose(j, s)
        s.problem_choice[:] = new_problem_choice  # JF(J) = JFF(J) for all J

        # 3. Decision-maker allocation (labels 140–150) ---------------------------------------
        dms_move = p.movement in (
            MovementCondition.BOTH_MOVE,
            MovementCondition.DECISION_MAKERS_ONLY,
        )
        new_dm_choice = np.full(p.n_decision_makers, NOT_ATTACHED, dtype=np.int64)  # KDCW
        for k in range(p.n_decision_makers):
            if not dms_move and s.dm_choice[k] != NOT_ATTACHED:
                new_dm_choice[k] = s.dm_choice[k]  # label 147
            else:
                new_dm_choice[k] = c.dm_allocation.choose(k, s)
        s.dm_choice[:] = new_dm_choice
        for k in range(p.n_decision_makers):
            if s.dm_choice[k] == NOT_ATTACHED:
                s.energy_reserve = s.energy_reserve + (
                    s.energy[k][t] * s.solution_coefficients[t]
                )  # XR
                s.dm_resting_periods += 1  # KS

        # 4. Energy required / expended (labels 160–199) --------------------------------------
        xsc = s.solution_coefficients[t]
        for i in range(p.n_choices):
            if s.choice_status[i] == INACTIVE:
                continue
            req = a.zero()  # XERC(I) = 0.0
            had = False
            for j in range(p.n_problems):
                if s.problem_status[j] == ACTIVE and s.problem_choice[j] == i:
                    req = req + s.problem_requirement[j]
                    had = True
            s.choice_requirement[i] = req
            if had:
                s.choice_ever_had_problems[i] = True
            energy = s.choice_energy[i]
            for k in range(p.n_decision_makers):
                if s.decision_structure[i, k] and s.dm_choice[k] == i:
                    energy = energy + xsc * s.energy[k][t]  # XEE(I) = XEE(I) + XSC(LT) * XEA(K, LT)
            s.choice_energy[i] = energy
        self._h_req[t] = s.requirement_as_floats()
        self._h_energy[t] = s.energy_as_floats()

        # 5. Decisions (labels 250–299) -------------------------------------------------------
        self._dm_detach_flag[:] = False
        for i in range(p.n_choices):
            if s.choice_status[i] != ACTIVE:
                continue
            if not c.choice_rule.is_made(i, s):
                continue
            s.energy_wastage = (s.energy_wastage + s.choice_energy[i]) - s.choice_requirement[
                i
            ]  # XS
            s.choice_status[i] = MADE
            solved = np.flatnonzero((s.problem_choice == i) & (s.problem_status == ACTIVE))
            # The program marks every problem with JF == I as solved; inactive problems never
            # carry JF == I at this point, so restricting to active ones is equivalent.
            s.problem_status[solved] = MADE
            if len(solved) > 0:
                style = DecisionStyle.RESOLUTION
            elif s.choice_ever_had_problems[i]:
                style = DecisionStyle.FLIGHT
            else:
                style = DecisionStyle.OVERSIGHT
            self._outcomes[i] = ChoiceOutcome(
                choice=i, period_made=lt, style=style, problems_solved=tuple(int(x) for x in solved)
            )
            if not dms_move:  # labels 261/262: frozen decision makers leave a made choice
                self._dm_detach_flag |= s.dm_choice == i

        # 6. Histories (labels 200–220) --------------------------------------------------------
        self._h_choices[t] = s.choice_status
        self._h_dms[t] = np.where(s.dm_choice == NOT_ATTACHED, 0, s.dm_choice + 1)
        s.dm_choice[self._dm_detach_flag] = NOT_ATTACHED
        prob_hist = np.where(s.problem_choice == NOT_ATTACHED, 0, s.problem_choice + 1)
        prob_hist = np.where(s.problem_status == INACTIVE, NOT_ENTERED_MARK, prob_hist)
        prob_hist = np.where(s.problem_status == MADE, SOLVED_MARK, prob_hist)
        self._h_problems[t] = prob_hist

    # ------------------------------------------------------------------ totals --------------
    @property
    def energy_reserve(self) -> float:
        return self.arith.to_float(self.state.energy_reserve)

    @property
    def energy_wastage(self) -> float:
        return self.arith.to_float(self.state.energy_wastage)
