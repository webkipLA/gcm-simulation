"""Parameters of the NetLogo garbage can model (the sliders, switches and choosers of the UI)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class Structure(str, Enum):
    """The three settings of the ``decision-structure`` / ``availability-structure`` /
    ``access-structure`` choosers."""

    ORGANIZED_ANARCHY = "organized anarchy"
    COMPETENT_HIERARCHY = "competent hierarchy"
    INCOMPETENT_HIERARCHY = "incompetent hierarchy"


@dataclass(frozen=True)
class NetLogoParameters:
    """All interface parameters of ``GarbageCan_simplified17.nlogox`` with their default values.

    The world is a ``world_width × world_height`` torus of unit patches (NetLogo view:
    ``min-pxcor 0, max-pxcor 49, min-pycor 0, max-pycor 49``, wrapping in both directions).
    """

    number_of_participants: int = 100
    number_of_opportunities: int = 100
    number_of_solutions: int = 100
    number_of_problems: int = 100
    min_ability: float = 0.0
    max_ability: float = 10.0
    min_efficiency: float = 0.0
    max_efficiency: float = 1.0
    min_difficulty: float = 0.0
    max_difficulty: float = 10.0
    span_of_control: int = 2
    decision_structure: Structure = Structure.COMPETENT_HIERARCHY
    availability_structure: Structure = Structure.COMPETENT_HIERARCHY
    access_structure: Structure = Structure.COMPETENT_HIERARCHY
    postpone: bool = True  # postpone?
    buckpass: bool = True  # buckpass?
    stop_at: int = 50_000  # stop-at (0 = never)
    world_width: int = 50
    world_height: int = 50
    seed: int | None = None

    @property
    def hierarchy_active(self) -> bool:
        """True iff at least one of the three structures is not an organized anarchy."""
        return any(
            s is not Structure.ORGANIZED_ANARCHY
            for s in (self.decision_structure, self.availability_structure, self.access_structure)
        )

    # thresholds used by the hierarchy rules: literally ``(max - min) / 2`` in the NetLogo code,
    # i.e. *half the range*, which equals the midpoint only when the minimum is 0.
    @property
    def ability_threshold(self) -> float:
        return (self.max_ability - self.min_ability) / 2

    @property
    def efficiency_threshold(self) -> float:
        return (self.max_efficiency - self.min_efficiency) / 2

    @property
    def difficulty_threshold(self) -> float:
        return (self.max_difficulty - self.min_difficulty) / 2

    def with_structures(self, structure: Structure) -> NetLogoParameters:
        """Set all three structures to the same value (as the BehaviorSpace experiments do)."""
        return replace(
            self,
            decision_structure=structure,
            availability_structure=structure,
            access_structure=structure,
        )


def behavior_space_experiments() -> dict[str, NetLogoParameters]:
    """The 12 BehaviorSpace experiments defined in the ``.nlogox`` file (3 structures × 4 flight
    combinations), each with 100 agents per breed, ranges [0, 10] / [0, 1] / [0, 10], span 2 and
    ``stop-at`` 50 000."""
    out: dict[str, NetLogoParameters] = {}
    flights = {"": (False, False), " P": (True, False), " BP": (False, True), " P+BP": (True, True)}
    names = {
        Structure.ORGANIZED_ANARCHY: "Organized Anarchy",
        Structure.COMPETENT_HIERARCHY: "Competent Hierarchy",
        Structure.INCOMPETENT_HIERARCHY: "Incompetent Hierarchy",
    }
    for structure, name in names.items():
        for suffix, (postpone, buckpass) in flights.items():
            out[name + suffix] = replace(
                NetLogoParameters().with_structures(structure), postpone=postpone, buckpass=buckpass
            )
    return out
