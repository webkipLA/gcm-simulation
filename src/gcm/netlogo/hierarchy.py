"""The fictional organizational hierarchy that ranks choice opportunities (``assign-importance``).

Opportunities are arranged in a pyramid with ``span_of_control`` times as many opportunities on
each level as on the level above (1, s, s², …). Levels are added until the pyramid holds at
least ``number_of_opportunities`` opportunities; the *hierarchy divide* is the number of
opportunities on the upper half of the levels (``int(levels / 2)`` levels). Opportunities with
``who <= hierarchy_divide`` are treated as **high-importance**, the others as low-importance.

Note that the comparison in the NetLogo code is ``<=``, so ``hierarchy_divide + 1`` opportunities
are high-importance (e.g. 8 of 100 for the default span of 2), which is reproduced here.
"""

from __future__ import annotations


def hierarchy_levels(number_of_opportunities: int, span_of_control: int) -> int:
    """Number of levels ``l`` of the smallest pyramid holding all opportunities."""
    level, added, total = 1, 1, 1
    while total < number_of_opportunities:
        total += span_of_control * added
        added *= span_of_control
        level += 1
    return level


def hierarchy_divide(number_of_opportunities: int, span_of_control: int) -> int:
    """Port of ``to assign-importance``: opportunities in the upper half of the pyramid."""
    levels = hierarchy_levels(number_of_opportunities, span_of_control)
    mid = levels // 2  # int (l / 2)
    level, added, total = 1, 1, 1
    while level < mid:
        total += span_of_control * added
        added *= span_of_control
        level += 1
    return total


def level_of(who: int, span_of_control: int) -> int:
    """1-based pyramid level of opportunity ``who`` (level 1 = the single top opportunity)."""
    level, added, total = 1, 1, 1
    while who >= total:
        total += span_of_control * added
        added *= span_of_control
        level += 1
    return level
