"""Mutable simulation state of the FORTRAN model, exposed read-only to pluggable rules."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from gcm.fortran.arithmetic import Arithmetic, ExactArithmetic

# Status codes of choices (ICS) and problems (JPS), identical to the FORTRAN program.
INACTIVE = 0
ACTIVE = 1
MADE = 2  # for choices: decision made; for problems: solved

# Sentinel used for "not attached" (FORTRAN uses 0 with 1-based ids; we use -1 with 0-based ids).
NOT_ATTACHED = -1
# Marks used in the *problem history* (KCBC).
SOLVED_MARK = 1000
NOT_ENTERED_MARK = -1


@dataclass
class FortranState:
    """All arrays of the FORTRAN program (0-based indices; periods are 1-based like ``LT``).

    Energy quantities are Python lists of backend numbers (floats, or emulated System/360
    values) so that the arithmetic backend is respected; status arrays are numpy int arrays.
    Attributes mirror the original variable names in comments so the port can be checked line by
    line against the appendix listing.
    """

    n_periods: int
    n_choices: int
    n_problems: int
    n_decision_makers: int
    arith: Arithmetic = field(default_factory=ExactArithmetic)

    period: int = 0  # LT (1-based; 0 = before the first period)

    # per choice
    choice_status: np.ndarray = field(init=False)  # ICS
    choice_requirement: list = field(init=False)  # XERC: energy required
    choice_energy: list = field(init=False)  # XEE: cumulative effective energy expended
    choice_ever_had_problems: np.ndarray = field(init=False)  # (added) for decision-style tagging

    # per problem
    problem_status: np.ndarray = field(init=False)  # JPS
    problem_choice: np.ndarray = field(init=False)  # JF  (-1 = not attached)
    problem_requirement: list = field(init=False)  # XERP

    # per decision maker
    dm_choice: np.ndarray = field(init=False)  # KDC (-1 = not attached)

    # structures (recomputed each period from the pluggable components)
    decision_structure: np.ndarray = field(init=False)  # IKA  shape (n_choices, n_dm), bool
    access_structure: np.ndarray = field(init=False)  # JIA  shape (n_problems, n_choices), bool
    energy: list = field(init=False)  # XEA  [dm][period]
    solution_coefficients: list = field(init=False)  # XSC [period]

    # running totals
    energy_reserve: object = None  # XR: effective energy of idle decision makers
    energy_wastage: object = None  # XS: effective energy in excess of requirement when made
    dm_resting_periods: int = 0  # KS

    def __post_init__(self) -> None:
        nc, npb, nd, nt = self.n_choices, self.n_problems, self.n_decision_makers, self.n_periods
        z = self.arith.zero
        self.choice_status = np.zeros(nc, dtype=np.int64)
        self.choice_requirement = [z() for _ in range(nc)]
        self.choice_energy = [z() for _ in range(nc)]
        self.choice_ever_had_problems = np.zeros(nc, dtype=bool)
        self.problem_status = np.zeros(npb, dtype=np.int64)
        self.problem_choice = np.full(npb, NOT_ATTACHED, dtype=np.int64)
        self.problem_requirement = [z() for _ in range(npb)]
        self.dm_choice = np.full(nd, NOT_ATTACHED, dtype=np.int64)
        self.decision_structure = np.ones((nc, nd), dtype=bool)
        self.access_structure = np.ones((npb, nc), dtype=bool)
        self.energy = [[z() for _ in range(nt)] for _ in range(nd)]
        self.solution_coefficients = [z() for _ in range(nt)]
        self.energy_reserve = z()
        self.energy_wastage = z()

    # -- convenience views -----------------------------------------------------------------
    @property
    def previous_period(self) -> int:
        """``LTT`` of the program: the previous period, clamped to 1 in the first period."""
        return max(self.period - 1, 1)

    def active_choices(self) -> np.ndarray:
        return np.flatnonzero(self.choice_status == ACTIVE)

    def active_problems(self) -> np.ndarray:
        return np.flatnonzero(self.problem_status == ACTIVE)

    def choice_deficit(self, choice: int):
        """``XERC(I) - XEE(I)``: energy still missing to make ``choice`` (may be negative)."""
        return self.choice_requirement[choice] - self.choice_energy[choice]

    # -- float views for reporting ----------------------------------------------------------
    def requirement_as_floats(self) -> np.ndarray:
        return np.array([self.arith.to_float(x) for x in self.choice_requirement])

    def energy_as_floats(self) -> np.ndarray:
        return np.array([self.arith.to_float(x) for x in self.choice_energy])
