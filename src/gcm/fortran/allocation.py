"""Rule-based defaults for the behavioural assumptions of the FORTRAN model.

These are line-by-line ports of the allocation loops (labels 120–127 for problems, 140–148 for
decision makers) and of the decision test (label 299). Ties are broken like the program does:
choices are scanned in index order and a candidate only replaces the incumbent if its deficit is
*strictly* smaller (``IF (deficit .GE. S) GO TO next``), so among exactly tied choices the
lowest-numbered (most important) wins. Whether two deficits are "exactly" tied is decided by the
arithmetic backend (see :mod:`gcm.fortran.arithmetic`).

Expression evaluation order follows FORTRAN's left-to-right rule for equal-precedence
operators, which matters for the emulated System/360 backend:
``XERP(J) + XERC(I) - XEE(I)`` is ``(XERP + XERC) - XEE`` and
``XERC(I) - XEE(I) - (XEA(K,LTT) * XSC(LTT))`` is ``(XERC - XEE) - (XEA * XSC)``.
"""

from __future__ import annotations

from gcm.fortran.state import ACTIVE, NOT_ATTACHED, FortranState


class ClosestToDecisionProblem:
    """Problem allocation assumption (Cohen, March & Olsen 1972, p. 4).

    Each active problem attaches to the accessible, active choice with the smallest *apparent*
    energy deficit at the end of the previous period. For the choice it is currently attached to
    (or if it is attached nowhere) the deficit is ``XERC - XEE``; for any other choice the
    problem's own requirement is added (``XERP + XERC - XEE``), i.e. the deficit the choice would
    have if the problem joined it.
    """

    name = "closest_to_decision"

    def choose(self, problem: int, state: FortranState) -> int:
        arith = state.arith
        current = int(state.problem_choice[problem])
        own = state.problem_requirement[problem]
        access = state.access_structure[problem]
        best_deficit = arith.const(1_000_000)  # S = 1000000
        best = NOT_ATTACHED
        for choice in range(state.n_choices):
            if state.choice_status[choice] != ACTIVE or not access[choice]:
                continue
            if current != NOT_ATTACHED and current != choice:
                deficit = (own + state.choice_requirement[choice]) - state.choice_energy[
                    choice
                ]  # label 123
            else:
                deficit = (
                    state.choice_requirement[choice] - state.choice_energy[choice]
                )  # label 122
            if arith.ge(deficit, best_deficit):  # strictly better only
                continue
            best_deficit, best = deficit, choice
        return best


class ClosestToDecisionDM:
    """Energy allocation assumption (Cohen, March & Olsen 1972, p. 4).

    Each decision maker allocates all of this period's energy to the eligible, active choice
    with the smallest energy deficit at the end of the previous period. Deficits are ``XERC - XEE``
    for the choice the decision maker is already attached to (or for all choices if idle) and
    ``XERC - XEE - own_effective_energy_of_previous_period`` for the other choices.
    """

    name = "closest_to_decision"

    def choose(self, decision_maker: int, state: FortranState) -> int:
        arith = state.arith
        current = int(state.dm_choice[decision_maker])
        ltt = state.previous_period - 1  # 0-based column of the previous period (clamped)
        own = state.energy[decision_maker][ltt] * state.solution_coefficients[ltt]
        eligible = state.decision_structure[:, decision_maker]
        best_deficit = arith.const(1_000_000)
        best = NOT_ATTACHED
        for choice in range(state.n_choices):
            if state.choice_status[choice] != ACTIVE or not eligible[choice]:
                continue
            deficit = state.choice_requirement[choice] - state.choice_energy[choice]
            if current != NOT_ATTACHED and current != choice:
                deficit = deficit - own  # label 143
            if arith.ge(deficit, best_deficit):
                continue
            best_deficit, best = deficit, choice
        return best


class EnergyAdditivityRule:
    """Energy additivity assumption: a choice is made as soon as the cumulative effective energy
    expended on it equals or exceeds the summed requirements of the problems attached to it
    (``IF (XERC(I) .GT. XEE(I)) GO TO 299``, i.e. *not* made only if requirement exceeds energy)."""

    name = "energy_additivity"

    def is_made(self, choice: int, state: FortranState) -> bool:
        return not state.arith.gt(state.choice_requirement[choice], state.choice_energy[choice])
