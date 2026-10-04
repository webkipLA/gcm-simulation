"""Reference structures in the orientation used throughout :mod:`gcm.contextual`.

All matrices in this subpackage are ``rows × opportunities``: entry ``[r, c]`` is True iff row
entity ``r`` (a participant, later also a problem) is permitted to enter opportunity ``c``. Both
axes are in importance order, index 0 being the most important element. This is the layout in
which Cohen, March & Olsen (1972, pp. 6–7) print the decision structure. The FORTRAN port stores
the transpose (``IKA[choice, decision_maker]``); the conversion happens in
:mod:`gcm.contextual.fortran_adapter` and nowhere else.
"""

from __future__ import annotations

import numpy as np

from gcm.common import StructureKind


def reference_matrix(kind: StructureKind | str, n_rows: int, n_cols: int) -> np.ndarray:
    """The pure structure ``kind`` for ``n_rows`` row entities and ``n_cols`` opportunities.

    For the square case this is exactly ``D0``, ``D1`` or ``D2`` of the paper:

    * unsegmented: everybody may enter everything;
    * hierarchical: row ``r`` may enter opportunity ``c`` iff ``c >= r`` (important rows reach
      many opportunities, important opportunities admit only important rows);
    * specialized: row ``r`` may enter opportunity ``c`` iff ``c == r``.

    For non-square shapes the ranks are compared as fractions of their axis, which reduces to the
    rules above when ``n_rows == n_cols``. The non-square forms are a convenience for role × type
    scenarios; they are not part of the 1972 paper.
    """
    kind = StructureKind(kind)
    r = np.arange(n_rows)[:, None]
    c = np.arange(n_cols)[None, :]
    if kind is StructureKind.UNSEGMENTED:
        return np.ones((n_rows, n_cols), dtype=bool)
    # opportunity class of a row: the opportunity index with the same relative rank
    own = (r * n_cols) // n_rows
    if kind is StructureKind.HIERARCHICAL:
        return np.ascontiguousarray(c >= own)
    return np.ascontiguousarray(c == own)


def reference_matrices(n_rows: int, n_cols: int) -> dict[str, np.ndarray]:
    """All three pure structures, keyed by their name."""
    return {kind.value: reference_matrix(kind, n_rows, n_cols) for kind in StructureKind}


__all__ = ["reference_matrices", "reference_matrix"]
