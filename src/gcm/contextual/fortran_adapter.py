"""The exported structure as a component of the FORTRAN port.

:class:`ContextualDecisionStructure` implements ``gcm.fortran.interfaces.DecisionStructure``:
``matrix(state)`` returns the boolean matrix the simulation expects, shape
``(n_choices, n_decision_makers)``. The exported structure is ``participants × opportunities``,
so this is the one place where the transpose happens.

Two modes:

``threshold``
    the binary matrix of the export is used as it is, in every period (the structure is fixed,
    as in the original program);
``sample``
    a new binary matrix is drawn from the yes shares when the component is created (once per
    simulation run), with a seed, so that every run of a seed series sees a different draw.
    Within a run the matrix stays fixed.

The access structure counterpart, :class:`ContextualAccessStructure`, is provided for the
problems × opportunities case so that the same export format can replace matrix ``A`` later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from gcm.contextual.structure_io import StructureExport
from gcm.fortran.state import FortranState

MODES = ("threshold", "sample")


def _check(export: StructureExport, row_entity: str, n_rows: int, n_cols: int) -> None:
    if export.row_entity != row_entity:
        raise ValueError(
            f"the export describes {export.row_entity}s × opportunities, "
            f"but this component needs {row_entity}s × opportunities"
        )
    if export.shape != (n_rows, n_cols):
        raise ValueError(
            f"the FORTRAN port needs {n_rows} {row_entity}s and {n_cols} opportunities "
            f"(the paper's fixed parameters), the export has {export.shape}"
        )


def _matrix(export: StructureExport, mode: str, seed: int | None) -> np.ndarray:
    if mode == "threshold":
        return export.binary.copy()
    if mode == "sample":
        return export.sample(np.random.default_rng(seed))
    raise ValueError(f"mode must be one of {MODES}")


@dataclass
class ContextualDecisionStructure:
    """``DecisionStructure.matrix(state)`` backed by an exported participants × opportunities
    structure. Row ``r`` of the export is decision maker ``r``, column ``c`` is choice ``c``."""

    export: StructureExport
    mode: str = "threshold"
    seed: int | None = None
    n_choices: int = 10
    n_decision_makers: int = 10
    name: str = field(init=False)
    _matrix: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _check(self.export, "participant", self.n_decision_makers, self.n_choices)
        drawn = _matrix(self.export, self.mode, self.seed)
        self._matrix = np.ascontiguousarray(drawn.T)  # IKA[choice, dm]
        suffix = f"{self.mode}" + (f"@{self.seed}" if self.mode == "sample" else "")
        self.name = f"contextual:{self.export.name}:{suffix}"

    @property
    def participants_by_opportunities(self) -> np.ndarray:
        """The matrix in the orientation of the export (for display and degeneracy checks)."""
        return self._matrix.T

    def matrix(self, state: FortranState) -> np.ndarray:
        return self._matrix


@dataclass
class ContextualAccessStructure:
    """``AccessStructure.matrix(state)`` backed by an exported problems × opportunities
    structure. The FORTRAN layout ``JIA[problem, choice]`` has the same orientation, so no
    transpose is needed here."""

    export: StructureExport
    mode: str = "threshold"
    seed: int | None = None
    n_choices: int = 10
    n_problems: int = 20
    name: str = field(init=False)
    _matrix: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _check(self.export, "problem", self.n_problems, self.n_choices)
        self._matrix = np.ascontiguousarray(_matrix(self.export, self.mode, self.seed))
        suffix = f"{self.mode}" + (f"@{self.seed}" if self.mode == "sample" else "")
        self.name = f"contextual:{self.export.name}:{suffix}"

    def matrix(self, state: FortranState) -> np.ndarray:
        return self._matrix


__all__ = ["MODES", "ContextualAccessStructure", "ContextualDecisionStructure"]
