"""Parameters of the FORTRAN garbage can simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from gcm.fortran import data


class MovementCondition(IntEnum):
    """The control variable ``NA`` of the FORTRAN program.

    All published results use ``BOTH_MOVE`` (NA = 1). The other values freeze problems and/or
    decision makers at the first choice they attach to.
    """

    BOTH_MOVE = 1  # problems and decision makers re-allocate every period
    DECISION_MAKERS_ONLY = 2  # problems stay where they first attach
    PROBLEMS_ONLY = 3  # decision makers stay where they first attach (detach when choice is made)
    NEITHER_MOVES = 4


class Load(IntEnum):
    """Net energy load (``IB`` = 0, 1, 2). Each problem requires ``1.1 × (IB + 1)`` energy."""

    LIGHT = 0
    MODERATE = 1
    HEAVY = 2

    @property
    def problem_energy(self) -> float:
        """Energy required per problem: 1.1 (light), 2.2 (moderate), 3.3 (heavy)."""
        return 1.1 * (int(self) + 1)


@dataclass(frozen=True)
class FortranParameters:
    """Fixed parameters plus the exogenous streams of the FORTRAN program.

    Defaults reproduce the paper's fixed parameters and entry-time condition (a)/(a).
    Indices in the entry-time tuples are 0-based element ids, values are 1-based periods.
    """

    n_periods: int = 20  # NTP
    n_choices: int = 10  # NCH
    n_problems: int = 20  # NPR
    n_decision_makers: int = 10  # NDM
    choice_entry_times: tuple[int, ...] = data.CHOICE_ENTRY_A  # ICH
    problem_entry_times: tuple[int, ...] = data.PROBLEM_ENTRY_A  # JET
    solution_coefficients: tuple[float, ...] = data.SOLUTION_COEFFICIENTS_CONSTANT  # XSC
    movement: MovementCondition = MovementCondition.BOTH_MOVE  # NA
    initial_choice_requirement: str = "1.1"
    """Value the program assigns to ``XERC(I)`` before a choice has ever been evaluated.

    It only matters for the attractiveness of a choice in the very first allocation step after
    activation (before its requirement is recomputed from attached problems). Kept as a decimal
    string so that every arithmetic backend converts it the way it converts other constants.
    """
    problem_energy_unit: str = "1.1"
    """``XERP(J) = IL * 1.1``: each problem requires ``(load + 1)`` times this unit."""
    arithmetic: str = "exact"
    """Arithmetic backend: ``"exact"`` (default), ``"float64"``, ``"ibm360"``, ``"ibm360-nearest"``.
    See :mod:`gcm.fortran.arithmetic`."""
    label: str = field(default="choices_a/problems_a", compare=False)

    def __post_init__(self) -> None:
        if len(self.choice_entry_times) != self.n_choices:
            raise ValueError("choice_entry_times must have one entry per choice")
        if len(self.problem_entry_times) != self.n_problems:
            raise ValueError("problem_entry_times must have one entry per problem")
        if len(self.solution_coefficients) != self.n_periods:
            raise ValueError("solution_coefficients must have one entry per period")

    @classmethod
    def from_entry_condition(cls, name: str, **overrides) -> FortranParameters:
        """Build parameters for one of the four named entry-time conditions."""
        choices, problems = data.ENTRY_CONDITIONS[name]
        return cls(
            choice_entry_times=choices, problem_entry_times=problems, label=name, **overrides
        )
