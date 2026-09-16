"""Exogenous input data of the original simulation (the "data cards" of the FORTRAN program).

Cohen, March & Olsen (1972, pp. 4–5) fix the following: 20 time periods, 10 choices, 10 decision
makers, 20 problems, a constant solution coefficient of 0.6, and two randomly generated entry
orders each for choices and problems. The arrays below are the *entry times* per choice/problem
(what the program reads as ``ICH`` and ``JET``), derived from the entry *orders* stated in the
paper. They coincide with the data cards printed at the end of the appendix.
"""

from __future__ import annotations

# --- Choice entry times: ICH(I) = period in which choice I (1..10) becomes active ---------------
# Order (a): choices enter one per period in the order 10, 7, 9, 5, 2, 3, 4, 1, 6, 8.
CHOICE_ENTRY_A: tuple[int, ...] = (8, 5, 6, 7, 4, 9, 2, 10, 3, 1)
# Order (b): 6, 5, 2, 10, 8, 9, 7, 4, 1, 3.
CHOICE_ENTRY_B: tuple[int, ...] = (9, 3, 10, 8, 2, 1, 7, 5, 6, 4)

# --- Problem entry times: JET(J) = period in which problem J (1..20) becomes visible -------------
# Order (a): two per period: 8, 20, 14, 16, 6, 7, 15, 17, 2, 13, 11, 19, 4, 9, 3, 12, 1, 10, 5, 18.
PROBLEM_ENTRY_A: tuple[int, ...] = (9, 5, 8, 7, 10, 3, 3, 1, 7, 9, 6, 8, 5, 2, 4, 2, 4, 10, 6, 1)
# Order (b): 4, 14, 11, 20, 3, 5, 2, 12, 1, 6, 8, 19, 7, 15, 16, 17, 10, 18, 9, 13.
PROBLEM_ENTRY_B: tuple[int, ...] = (5, 4, 3, 1, 3, 5, 7, 6, 10, 9, 2, 4, 10, 1, 7, 8, 8, 9, 6, 2)

# --- Solution coefficients XSC(LT), one per period ----------------------------------------------
# All reported results use the constant series.
SOLUTION_COEFFICIENTS_CONSTANT: tuple[float, ...] = (0.6,) * 20
# Footnote 3 of the paper: a time-varying series that yields consistent conclusions.
SOLUTION_COEFFICIENTS_VARIABLE: tuple[float, ...] = (
    1.0,
    0.9,
    0.7,
    0.3,
    0.1,
    0.1,
    0.3,
    0.7,
    0.9,
    1.0,
    0.6,
    0.6,
    0.6,
    0.6,
    0.6,
    0.6,
    0.6,
    0.6,
    0.6,
    0.6,
)

ENTRY_CONDITIONS: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {
    "choices_a/problems_a": (CHOICE_ENTRY_A, PROBLEM_ENTRY_A),
    "choices_a/problems_b": (CHOICE_ENTRY_A, PROBLEM_ENTRY_B),
    "choices_b/problems_a": (CHOICE_ENTRY_B, PROBLEM_ENTRY_A),
    "choices_b/problems_b": (CHOICE_ENTRY_B, PROBLEM_ENTRY_B),
}
"""The four combinations of choice and problem entry times used in the paper (324 = 81 × 4)."""


def order_to_entry_times(order: tuple[int, ...], per_period: int) -> tuple[int, ...]:
    """Convert an entry *order* (as printed in the paper) into entry *times* per element.

    ``order[k]`` is the 1-based id of the element entering in slot ``k``; ``per_period`` elements
    enter per period. Returns a tuple indexed by element id − 1.
    """
    times = [0] * len(order)
    for slot, element in enumerate(order):
        times[element - 1] = slot // per_period + 1
    return tuple(times)


# Sanity: the tuples above must be consistent with the orders printed in the paper.
assert order_to_entry_times((10, 7, 9, 5, 2, 3, 4, 1, 6, 8), 1) == CHOICE_ENTRY_A
assert order_to_entry_times((6, 5, 2, 10, 8, 9, 7, 4, 1, 3), 1) == CHOICE_ENTRY_B
assert (
    order_to_entry_times((8, 20, 14, 16, 6, 7, 15, 17, 2, 13, 11, 19, 4, 9, 3, 12, 1, 10, 5, 18), 2)
    == PROBLEM_ENTRY_A
)
assert (
    order_to_entry_times((4, 14, 11, 20, 3, 5, 2, 12, 1, 6, 8, 19, 7, 15, 16, 17, 10, 18, 9, 13), 2)
    == PROBLEM_ENTRY_B
)
