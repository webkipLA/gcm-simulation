"""Extension points of the FORTRAN garbage can model.

Every behavioural assumption of Cohen, March & Olsen's program is factored into one of the
protocols below. The simulation core (:mod:`gcm.fortran.model`) only talks to these
interfaces, so an alternative implementation (for example one that asks a language model which
participants may attend which choice) can be dropped in without touching the core.

Component map (paper section → protocol → default implementation):

==========================  ==================================  ==================================
Paper                       Protocol                            Rule-based default
==========================  ==================================  ==================================
Decision structure D        :class:`DecisionStructure`          ``structures.decision_structure``
Access structure A          :class:`AccessStructure`            ``structures.access_structure``
Energy distribution E       :class:`EnergyDistribution`         ``structures.energy_distribution``
Energy allocation assumpt.  :class:`DecisionMakerAllocationRule``allocation.ClosestToDecisionDM``
Problem allocation assumpt. :class:`ProblemAllocationRule`      ``allocation.ClosestToDecisionProblem``
Energy additivity assumpt.  :class:`ChoiceRule`                 ``allocation.EnergyAdditivityRule``
==========================  ==================================  ==================================

The structures are queried **every period** (``matrix(state)``), not once at setup. The classic
implementations simply return a cached constant matrix; a dynamic implementation may return a
different matrix each period, which is what a fluid, LLM-mediated participation structure needs.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from gcm.fortran.arithmetic import Arithmetic
from gcm.fortran.state import FortranState


@runtime_checkable
class DecisionStructure(Protocol):
    """Which decision makers are eligible to participate in which choices (matrix ``D``).

    ``matrix(state)`` must return a boolean array of shape ``(n_choices, n_decision_makers)``
    (the FORTRAN ``IKA(I, K)`` layout): entry ``[i, k]`` is True iff decision maker ``k`` may
    participate in choice ``i``.
    """

    name: str

    def matrix(self, state: FortranState) -> np.ndarray: ...


@runtime_checkable
class AccessStructure(Protocol):
    """Which choices are accessible to which problems (matrix ``A``).

    ``matrix(state)`` must return a boolean array of shape ``(n_problems, n_choices)`` (the
    FORTRAN ``JIA(J, I)`` layout): entry ``[j, i]`` is True iff problem ``j`` has access to
    choice ``i``.
    """

    name: str

    def matrix(self, state: FortranState) -> np.ndarray: ...


@runtime_checkable
class EnergyDistribution(Protocol):
    """Potential energy each decision maker can provide in each period (matrix ``XEA``).

    ``matrix(n_decision_makers, n_periods, arith)`` returns a nested list ``[dm][period]`` of
    numbers created with the given arithmetic backend (``arith.const(...)``).
    """

    name: str

    def matrix(self, n_decision_makers: int, n_periods: int, arith: Arithmetic) -> list[list]: ...


@runtime_checkable
class ProblemAllocationRule(Protocol):
    """The *problem allocation assumption*: to which (accessible, active) choice a problem attaches.

    Returns the 0-based choice index, or ``-1`` for "attached to no choice". Called once per
    active problem per period, **before** decision makers are allocated, with ``state`` reflecting
    the end of the previous period (``choice_requirement`` / ``choice_energy`` are stale by
    design; this is what the program does).
    """

    name: str

    def choose(self, problem: int, state: FortranState) -> int: ...


@runtime_checkable
class DecisionMakerAllocationRule(Protocol):
    """The *energy allocation assumption*: to which (eligible, active) choice a decision maker
    devotes this period's energy.

    Returns the 0-based choice index, or ``-1`` for "idle". Called once per decision maker per
    period, after problems have been (re-)attached for the period.
    """

    name: str

    def choose(self, decision_maker: int, state: FortranState) -> int: ...


@runtime_checkable
class ChoiceRule(Protocol):
    """The *energy additivity assumption*: when is an active choice made?

    Evaluated once per active choice per period after requirements and energies were updated.
    """

    name: str

    def is_made(self, choice: int, state: FortranState) -> bool: ...
