"""The four breeds of the NetLogo model and the patch state.

``who`` numbers are assigned in creation order exactly as in ``setup``: opportunities first
(``0 … n_opp − 1``), then participants, solutions and problems. For opportunities the ``who``
number doubles as the importance rank: **lower ``who`` = more important** (the hierarchy rules in
the code compare ``who <= hierarchy-divide``; the comment in ``setup`` claiming the opposite is a
documentation slip in the original file).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Breed(IntEnum):
    OPPORTUNITY = 0
    PARTICIPANT = 1
    SOLUTION = 2
    PROBLEM = 3


class PatchColor(IntEnum):
    """Patch colours are *model state* in the NetLogo implementation, not just display:
    ``WHITE`` marks a blocked decision process (used by flight conditions and the monitor),
    ``BROWN`` marks the patch under a flying pair, ``BLACK`` is the only colour ``free-spot``
    accepts, ``LIME``/``SKY`` mark last tick's resolutions/oversights."""

    BLACK = 0
    WHITE = 1
    LIME = 2  # decision by resolution
    SKY = 3  # decision by oversight
    BROWN = 4  # flying pair


@dataclass(eq=False)
class Agent:
    who: int
    x: int
    y: int
    blocked: bool = False  # blocked?

    @property
    def patch(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass(eq=False)
class Opportunity(Agent):
    last_movement: int = 0
    charged: bool = False  # charged?  (carrying a postponed problem)
    with_problem: Problem | None = None
    breed = Breed.OPPORTUNITY


@dataclass(eq=False)
class Participant(Agent):
    ability: float = 0.0
    last_movement: int = 0
    charged: bool = False  # charged?  (carrying a buck-passed problem)
    with_problem: Problem | None = None
    breed = Breed.PARTICIPANT


@dataclass(eq=False)
class Solution(Agent):
    efficiency: float = 0.0
    breed = Breed.SOLUTION


@dataclass(eq=False)
class Problem(Agent):
    difficulty: float = 0.0
    postponed: bool = False  # postponed?
    to_opportunity: Opportunity | None = None
    passed: bool = False  # passed?
    to_participant: Participant | None = None
    since: int = 0  # tick at which the current flight began
    breed = Breed.PROBLEM


@dataclass(eq=False)
class PatchAgents:
    """The agents currently on one patch, by breed (the ``-here`` / ``-on`` agentsets)."""

    opportunities: list[Opportunity] = field(default_factory=list)
    participants: list[Participant] = field(default_factory=list)
    solutions: list[Solution] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.opportunities or self.participants or self.solutions or self.problems)

    def all(self) -> list[Agent]:
        return [*self.opportunities, *self.participants, *self.solutions, *self.problems]
