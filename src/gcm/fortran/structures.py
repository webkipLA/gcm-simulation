"""The nine pure organizational structures of Cohen, March & Olsen (1972, pp. 5–7).

All matrices are generated exactly as in the FORTRAN program (labels 502/504 for the decision
structure, 532/534 for the access structure, 570/580 for the energy distribution). Element ids
are 0-based here; "important" elements are the low-numbered ones, as in the paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from gcm.common import StructureKind
from gcm.fortran.arithmetic import Arithmetic
from gcm.fortran.state import FortranState


# --------------------------------------------------------------------------------------------
# Decision structure D  (v decision makers × m choices; stored as IKA[choice, dm])
# --------------------------------------------------------------------------------------------
@dataclass
class StaticDecisionStructure:
    """A constant decision structure given as a boolean matrix ``[choice, decision_maker]``."""

    _matrix: np.ndarray
    name: str = "custom"

    def matrix(self, state: FortranState) -> np.ndarray:
        return self._matrix


def decision_structure(
    kind: StructureKind, n_choices: int = 10, n_dm: int = 10
) -> StaticDecisionStructure:
    """Build ``D0`` (unsegmented), ``D1`` (hierarchical) or ``D2`` (specialized).

    * unsegmented: every decision maker may participate in every choice;
    * hierarchical: decision maker ``k`` may participate in choice ``i`` iff ``i >= k``
      (important people take part in many choices; important choices need important people);
    * specialized: decision maker ``k`` may participate in choice ``i`` iff ``i == k``.
    """
    i = np.arange(n_choices)[:, None]
    k = np.arange(n_dm)[None, :]
    if kind is StructureKind.UNSEGMENTED:
        m = np.ones((n_choices, n_dm), dtype=bool)
    elif kind is StructureKind.HIERARCHICAL:
        m = i >= k  # FORTRAN label 502: IF (I .GE. J) keep 1
    elif kind is StructureKind.SPECIALIZED:
        m = i == k  # FORTRAN label 504: IF (J .EQ. I) keep 1
    else:  # pragma: no cover
        raise ValueError(kind)
    return StaticDecisionStructure(np.ascontiguousarray(m), name=f"D_{kind.value}")


# --------------------------------------------------------------------------------------------
# Access structure A  (w problems × m choices; stored as JIA[problem, choice])
# --------------------------------------------------------------------------------------------
@dataclass
class StaticAccessStructure:
    """A constant access structure given as a boolean matrix ``[problem, choice]``."""

    _matrix: np.ndarray
    name: str = "custom"

    def matrix(self, state: FortranState) -> np.ndarray:
        return self._matrix


def access_structure(
    kind: StructureKind, n_problems: int = 20, n_choices: int = 10
) -> StaticAccessStructure:
    """Build ``A0`` (unsegmented), ``A1`` (hierarchical) or ``A2`` (specialized).

    With the paper's sizes (20 problems, 10 choices) there are two problems per choice "rank":

    * unsegmented: every problem has access to every choice;
    * hierarchical: problem ``j`` has access to choice ``i`` iff ``j + 1 <= 2 (i + 1)`` (1-based:
      ``J <= 2 I``); important problems reach many choices, important choices only admit
      important problems;
    * specialized: problems ``2i`` and ``2i + 1`` have access to choice ``i`` only.
    """
    j1 = np.arange(1, n_problems + 1)[:, None]  # 1-based problem ids, as in the program
    i1 = np.arange(1, n_choices + 1)[None, :]  # 1-based choice ids
    if kind is StructureKind.UNSEGMENTED:
        m = np.ones((n_problems, n_choices), dtype=bool)
    elif kind is StructureKind.HIERARCHICAL:
        m = (j1 - i1) <= i1  # FORTRAN label 532: IF ((I - J) .GT. J) skip  ⇔ keep iff I <= 2J
    elif kind is StructureKind.SPECIALIZED:
        m = (j1 == 2 * i1) | (j1 == 2 * i1 - 1)  # label 534: JIA(2J, J) = JIA(2J-1, J) = 1
    else:  # pragma: no cover
        raise ValueError(kind)
    return StaticAccessStructure(np.ascontiguousarray(m), name=f"A_{kind.value}")


# --------------------------------------------------------------------------------------------
# Energy distribution E  (v decision makers × NTP periods; stored as XEA[dm, period])
# --------------------------------------------------------------------------------------------
class EnergyDistributionKind:
    IMPORTANT_LESS = 0  # E0: important people have less energy (0.1 … 1.0)
    EQUAL = 1  # E1: everyone 0.55
    IMPORTANT_MORE = 2  # E2: important people have more energy (1.0 … 0.1)


@dataclass
class StaticEnergyDistribution:
    """A time-constant energy vector (decimal strings or floats) broadcast over all periods."""

    per_decision_maker: tuple
    name: str = "custom"

    def matrix(self, n_decision_makers: int, n_periods: int, arith: Arithmetic) -> list[list]:
        if len(self.per_decision_maker) != n_decision_makers:
            raise ValueError("energy vector length must equal the number of decision makers")
        return [[arith.const(e) for _ in range(n_periods)] for e in self.per_decision_maker]


@dataclass
class ClassicEnergyDistribution:
    """``E0``, ``E1`` or ``E2`` computed exactly as the FORTRAN loop 570/580 does.

    * ``EQUAL``:          ``XEA = 0.55``
    * ``IMPORTANT_LESS``: ``XEA = XXA / 10.0``          (XXA = 1-based decision-maker id)
    * ``IMPORTANT_MORE``: ``XEA = (11.0 - XXA) / 10.0``

    Total energy per period is 5.5 in every case (for ten decision makers). The divisions are
    carried out in the arithmetic backend so that the emulated System/360 backend reproduces
    the truncated values the original machine held.
    """

    kind: int
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = {0: "E_important_less", 1: "E_equal", 2: "E_important_more"}[self.kind]

    def matrix(self, n_decision_makers: int, n_periods: int, arith: Arithmetic) -> list[list]:
        ten, eleven = arith.const("10.0"), arith.const("11.0")
        rows = []
        for k in range(1, n_decision_makers + 1):
            if self.kind == EnergyDistributionKind.EQUAL:
                e = arith.const("0.55")
            elif self.kind == EnergyDistributionKind.IMPORTANT_LESS:
                e = arith.const(k) / ten  # label 570
            elif self.kind == EnergyDistributionKind.IMPORTANT_MORE:
                e = (eleven - arith.const(k)) / ten
            else:  # pragma: no cover
                raise ValueError(self.kind)
            rows.append([e for _ in range(n_periods)])
        return rows


def energy_distribution(kind: int, n_dm: int = 10) -> ClassicEnergyDistribution:
    """Build ``E0``, ``E1`` or ``E2`` (see :class:`ClassicEnergyDistribution`)."""
    return ClassicEnergyDistribution(kind)


@dataclass(frozen=True)
class OrganizationalVariant:
    """One of the 81 organizational situations: (load, access, decision, energy) indices."""

    load: int  # IB: 0 light, 1 moderate, 2 heavy
    access: StructureKind  # JA
    decision: StructureKind  # JD
    energy: int  # JE: 0, 1, 2

    _kinds: tuple[StructureKind, ...] = field(
        default=(StructureKind.UNSEGMENTED, StructureKind.HIERARCHICAL, StructureKind.SPECIALIZED),
        repr=False,
        compare=False,
    )

    @property
    def code(self) -> str:
        """Four-digit code ``load access decision energy`` used in Table 5 of the paper."""
        return f"{self.load}{self._kinds.index(self.access)}{self._kinds.index(self.decision)}{self.energy}"

    @classmethod
    def from_code(cls, code: str) -> OrganizationalVariant:
        kinds = (StructureKind.UNSEGMENTED, StructureKind.HIERARCHICAL, StructureKind.SPECIALIZED)
        b, a, d, e = (int(c) for c in code)
        return cls(load=b, access=kinds[a], decision=kinds[d], energy=e)

    @classmethod
    def all(cls) -> list[OrganizationalVariant]:
        """The 81 variants in the program's loop order (load, access, decision, energy)."""
        kinds = (StructureKind.UNSEGMENTED, StructureKind.HIERARCHICAL, StructureKind.SPECIALIZED)
        return [
            cls(load=b, access=a, decision=d, energy=e)
            for b in range(3)
            for a in kinds
            for d in kinds
            for e in range(3)
        ]
