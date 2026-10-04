"""From answers to structures: shares, intervals, binarization, agreement and distances.

All matrices are ``rows × opportunities`` in the importance order of the scenario (see
:mod:`gcm.contextual.references`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from gcm.contextual.scenario import Scenario

Z_95 = 1.959963984540054


class UndeterminedCellsError(ValueError):
    """Some cells have no valid answer, so no yes share and no binary value exist for them."""


@dataclass
class StructureEstimate:
    """Counts per cell from one or several runs of the same scenario."""

    scenario_id: str
    row_ids: tuple[str, ...]
    col_ids: tuple[str, ...]
    yes: np.ndarray  # valid answers "eligible: true"
    valid: np.ndarray  # valid answers
    invalid: np.ndarray  # answers of the model that could not be interpreted
    errors: np.ndarray  # calls that failed (no answer at all)
    label: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def share(self) -> np.ndarray:
        """Yes share per cell; NaN where no valid answer exists."""
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(self.valid > 0, self.yes / self.valid, np.nan)

    def wilson(self, z: float = Z_95) -> tuple[np.ndarray, np.ndarray]:
        return wilson_interval(self.yes, self.valid, z)

    @property
    def n_answers(self) -> int:
        return int(self.valid.sum() + self.invalid.sum() + self.errors.sum())

    @property
    def invalid_share(self) -> float:
        n = self.n_answers
        return float((self.invalid.sum() + self.errors.sum()) / n) if n else float("nan")


def aggregate(
    records: Iterable[dict], scenario: Scenario, label: str = "", meta: dict | None = None
) -> StructureEstimate:
    """Count the answers of ``records`` per cell. Invalid answers and failed calls are counted
    separately and never enter the yes share."""
    rows = {r: i for i, r in enumerate(scenario.row_ids)}
    cols = {c: i for i, c in enumerate(scenario.col_ids)}
    shape = scenario.shape
    yes, valid = np.zeros(shape, dtype=int), np.zeros(shape, dtype=int)
    invalid, errors = np.zeros(shape, dtype=int), np.zeros(shape, dtype=int)
    for record in records:
        r = rows[record["row_id"]]
        for cell in record["cells"]:
            c = cols[cell["col_id"]]
            if record.get("error"):
                errors[r, c] += 1
            elif cell["eligible"] is None:
                invalid[r, c] += 1
            else:
                valid[r, c] += 1
                yes[r, c] += int(cell["eligible"])
    return StructureEstimate(
        scenario.id,
        scenario.row_ids,
        scenario.col_ids,
        yes,
        valid,
        invalid,
        errors,
        label,
        dict(meta or {}),
    )


def wilson_interval(yes, n, z: float = Z_95) -> tuple[np.ndarray, np.ndarray]:
    """Wilson score interval for a proportion; (NaN, NaN) where ``n == 0``."""
    yes, n = np.asarray(yes, dtype=float), np.asarray(n, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = yes / n
        denom = 1 + z**2 / n
        centre = (p + z**2 / (2 * n)) / denom
        half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    low = np.where(n > 0, np.clip(centre - half, 0.0, 1.0), np.nan)
    high = np.where(n > 0, np.clip(centre + half, 0.0, 1.0), np.nan)
    return low, high


# -------------------------------------------------------------------------------- binarization
def _undetermined(share: np.ndarray) -> list[tuple[int, int]]:
    return [(int(r), int(c)) for r, c in np.argwhere(np.isnan(share))]


def binarize(share: np.ndarray, threshold: float = 0.5, on_missing: str = "error") -> np.ndarray:
    """Eligible iff ``share >= threshold``.

    Cells without any valid answer have no share. By default that is an error, because a
    default would silently put a value into the structure. ``on_missing="deny"`` or ``"allow"``
    state the choice explicitly.
    """
    share = np.asarray(share, dtype=float)
    missing = np.isnan(share)
    if missing.any():
        if on_missing == "error":
            raise UndeterminedCellsError(
                f"{int(missing.sum())} cell(s) without a valid answer: {_undetermined(share)}"
            )
        if on_missing not in ("deny", "allow"):
            raise ValueError("on_missing must be 'error', 'deny' or 'allow'")
    out = np.where(missing, on_missing == "allow", share >= threshold)
    return np.ascontiguousarray(out, dtype=bool)


def sample_binary(share: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One binary matrix drawn cell by cell with the yes shares as probabilities."""
    share = np.asarray(share, dtype=float)
    if np.isnan(share).any():
        raise UndeterminedCellsError(f"cells without a valid answer: {_undetermined(share)}")
    return np.ascontiguousarray(rng.random(share.shape) < share)


def uncertain_cells(estimate: StructureEstimate, threshold: float = 0.5) -> np.ndarray:
    """Cells whose Wilson interval contains the threshold (or that have no valid answer)."""
    low, high = estimate.wilson()
    return np.isnan(low) | ((low < threshold) & (high >= threshold))


def degeneracy(binary: np.ndarray, row_ids, col_ids) -> dict[str, list[str]]:
    """Rows without any eligible opportunity and opportunities nobody may enter.

    Such structures are reported, not repaired: a participant without opportunity never works on
    a choice, and an opportunity without participants can never be decided.
    """
    binary = np.asarray(binary, dtype=bool)
    return {
        "rows_without_opportunity": [r for r, any_ in zip(row_ids, binary.any(axis=1)) if not any_],
        "opportunities_without_row": [
            c for c, any_ in zip(col_ids, binary.any(axis=0)) if not any_
        ],
    }


# ------------------------------------------------------------------------ agreement, distances
def cohen_kappa(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's kappa of two binary matrices over their cells; NaN if chance agreement is 1."""
    a, b = np.asarray(a, dtype=bool).ravel(), np.asarray(b, dtype=bool).ravel()
    po = float((a == b).mean())
    pe = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    return float("nan") if pe >= 1.0 else (po - pe) / (1 - pe)


def agreement_table(
    estimates: Mapping[str, StructureEstimate], threshold: float = 0.5
) -> pd.DataFrame:
    """Pairwise agreement of estimates (e.g. across models or representations).

    For each pair: share of identical binary cells, Cohen's kappa and the mean absolute
    difference of the yes shares, over the cells determined in both estimates.
    """
    labels = list(estimates)
    rows = []
    for i, la in enumerate(labels):
        for lb in labels[i + 1 :]:
            sa, sb = estimates[la].share, estimates[lb].share
            both = ~np.isnan(sa) & ~np.isnan(sb)
            ba, bb = sa[both] >= threshold, sb[both] >= threshold
            rows.append(
                {
                    "a": la,
                    "b": lb,
                    "cells": int(both.sum()),
                    "agreement": float((ba == bb).mean()) if both.any() else float("nan"),
                    "kappa": cohen_kappa(ba, bb) if both.any() else float("nan"),
                    "mean_abs_share_diff": float(np.abs(sa[both] - sb[both]).mean())
                    if both.any()
                    else float("nan"),
                }
            )
    return pd.DataFrame(
        rows, columns=["a", "b", "cells", "agreement", "kappa", "mean_abs_share_diff"]
    )


def distances(
    share: np.ndarray, references: Mapping[str, np.ndarray], threshold: float = 0.5
) -> pd.DataFrame:
    """Distance of one structure to each reference structure.

    ``hamming`` counts differing binary cells, ``hamming_share`` divides by the number of
    compared cells, ``jaccard`` is the overlap of the permitted pairs, and ``mean_abs_error`` is
    the mean absolute difference between yes share and reference. Cells without a valid answer
    are left out and reported in ``cells``.
    """
    share = np.asarray(share, dtype=float)
    known = ~np.isnan(share)
    binary = share >= threshold
    rows = []
    for name, ref in references.items():
        ref = np.asarray(ref, dtype=bool)
        diff = int((binary[known] != ref[known]).sum())
        union = int((binary[known] | ref[known]).sum())
        inter = int((binary[known] & ref[known]).sum())
        n = int(known.sum())
        rows.append(
            {
                "reference": name,
                "cells": n,
                "hamming": diff,
                "hamming_share": diff / n if n else float("nan"),
                "jaccard": inter / union if union else 1.0,
                "mean_abs_error": float(np.abs(share[known] - ref[known]).mean())
                if n
                else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def nearest_reference(
    share: np.ndarray, references: Mapping[str, np.ndarray], threshold: float = 0.5
) -> str:
    """Name of the closest reference (Hamming distance; ties go to the first in ``references``)."""
    table = distances(share, references, threshold)
    return str(table.loc[table["hamming"].idxmin(), "reference"])


def distance_table(
    estimates: Mapping[str, StructureEstimate],
    references: Mapping[str, np.ndarray],
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Hamming share of every estimate to every reference, plus the nearest reference."""
    rows = []
    for label, estimate in estimates.items():
        table = distances(estimate.share, references, threshold).set_index("reference")
        row = {"estimate": label, **table["hamming_share"].to_dict()}
        row["nearest"] = str(table["hamming"].idxmin())
        rows.append(row)
    return pd.DataFrame(rows)


__all__ = [
    "StructureEstimate",
    "UndeterminedCellsError",
    "aggregate",
    "agreement_table",
    "binarize",
    "cohen_kappa",
    "degeneracy",
    "distance_table",
    "distances",
    "nearest_reference",
    "sample_binary",
    "uncertain_cells",
    "wilson_interval",
]
