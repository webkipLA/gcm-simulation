"""Vocabulary shared by both re-implementations."""

from __future__ import annotations

from enum import Enum


class DecisionStyle(str, Enum):
    """The three mutually exclusive ways a choice can be made (Cohen, March & Olsen 1972, p. 8).

    RESOLUTION
        The choice is made while problems are attached to it; those problems are solved.
        Choices that involve *both* flight and resolution count as resolution (paper convention).
    OVERSIGHT
        The choice is made before any problem ever attached itself to it.
    FLIGHT
        Problems were attached to the choice at some earlier point but had all left when the
        choice was made; the decision resolves nothing.
    """

    RESOLUTION = "resolution"
    OVERSIGHT = "oversight"
    FLIGHT = "flight"


class StructureKind(str, Enum):
    """The three pure structural arrangements of Cohen, March & Olsen (1972)."""

    UNSEGMENTED = "unsegmented"
    HIERARCHICAL = "hierarchical"
    SPECIALIZED = "specialized"


__all__ = ["DecisionStyle", "StructureKind"]
