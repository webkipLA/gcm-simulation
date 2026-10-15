"""The exported structure: the only thing a simulation ever sees of the LLM experiment.

A structure file holds both matrices (yes shares and the binary structure) with their labels and
the provenance of the answers. The simulations load it through
:mod:`gcm.contextual.fortran_adapter` and :mod:`gcm.contextual.netlogo_adapter`; they never call
a language model, so simulation speed does not depend on any model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from gcm.contextual.aggregate import StructureEstimate, binarize, degeneracy, sample_binary
from gcm.contextual.scenario import Scenario

FORMAT = "gcm-contextual-structure/1"


@dataclass
class StructureExport:
    """Probability matrix and binary structure, ``rows × opportunities`` in importance order."""

    scenario_id: str
    row_entity: str
    row_ids: tuple[str, ...]
    col_ids: tuple[str, ...]
    row_labels: tuple[str, ...]
    col_labels: tuple[str, ...]
    probability: np.ndarray  # yes shares (NaN = no valid answer)
    valid_n: np.ndarray
    binary: np.ndarray
    binarization: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    name: str = ""

    def __post_init__(self) -> None:
        shape = (len(self.row_ids), len(self.col_ids))
        self.probability = np.asarray(self.probability, dtype=float)
        self.valid_n = np.asarray(self.valid_n, dtype=int)
        self.binary = np.asarray(self.binary, dtype=bool)
        for what in (self.probability, self.valid_n, self.binary):
            if what.shape != shape:
                raise ValueError(f"matrices must have shape {shape} (rows × opportunities)")

    @property
    def shape(self) -> tuple[int, int]:
        return self.binary.shape

    @property
    def degenerate(self) -> dict[str, list[str]]:
        return degeneracy(self.binary, self.row_ids, self.col_ids)

    def sample(self, rng: np.random.Generator) -> np.ndarray:
        """A binary matrix drawn from the yes shares (the probabilistic mode)."""
        return sample_binary(self.probability, rng)

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_estimate(
        cls,
        estimate: StructureEstimate,
        scenario: Scenario,
        *,
        threshold: float = 0.5,
        on_missing: str = "error",
        language: str = "en",
        name: str = "",
    ) -> StructureExport:
        share = estimate.share
        return cls(
            scenario_id=scenario.id,
            row_entity=scenario.row_entity,
            row_ids=scenario.row_ids,
            col_ids=scenario.col_ids,
            row_labels=scenario.row_labels(language),
            col_labels=scenario.col_labels(language),
            probability=share,
            valid_n=estimate.valid,
            binary=binarize(share, threshold, on_missing),
            binarization={"mode": "threshold", "threshold": threshold, "on_missing": on_missing},
            provenance={
                "label": estimate.label,
                "created": datetime.now(UTC).isoformat(timespec="seconds"),
                "invalid_answers": int(estimate.invalid.sum()),
                "failed_calls": int(estimate.errors.sum()),
                **estimate.meta,
            },
            name=name or estimate.label or scenario.id,
        )

    @classmethod
    def from_matrix(
        cls, binary: np.ndarray, scenario: Scenario, *, language: str = "en", name: str = ""
    ) -> StructureExport:
        """A structure given directly as a 0/1 matrix (rule-based references, tests)."""
        binary = np.asarray(binary, dtype=bool)
        return cls(
            scenario_id=scenario.id,
            row_entity=scenario.row_entity,
            row_ids=scenario.row_ids,
            col_ids=scenario.col_ids,
            row_labels=scenario.row_labels(language),
            col_labels=scenario.col_labels(language),
            probability=binary.astype(float),
            valid_n=np.zeros(binary.shape, dtype=int),
            binary=binary,
            binarization={"mode": "given"},
            provenance={"source": "matrix given directly, no LLM involved"},
            name=name or scenario.id,
        )

    # ------------------------------------------------------------------ files
    def to_dict(self) -> dict:
        return {
            "format": FORMAT,
            "name": self.name,
            "scenario_id": self.scenario_id,
            "row_entity": self.row_entity,
            "orientation": "rows x opportunities, both in importance order (first = most important)",
            "row_ids": list(self.row_ids),
            "col_ids": list(self.col_ids),
            "row_labels": list(self.row_labels),
            "col_labels": list(self.col_labels),
            "probability": [
                [None if np.isnan(v) else round(float(v), 6) for v in row]
                for row in self.probability
            ],
            "valid_n": self.valid_n.tolist(),
            "binary": ["".join("1" if v else "0" for v in row) for row in self.binary],
            "binarization": self.binarization,
            "degenerate": self.degenerate,
            "provenance": self.provenance,
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return path

    @classmethod
    def load(cls, path: str | Path) -> StructureExport:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format") != FORMAT:
            raise ValueError(f"{path}: not a {FORMAT} file")
        return cls(
            scenario_id=data["scenario_id"],
            row_entity=data["row_entity"],
            row_ids=tuple(data["row_ids"]),
            col_ids=tuple(data["col_ids"]),
            row_labels=tuple(data["row_labels"]),
            col_labels=tuple(data["col_labels"]),
            probability=np.array(
                [[np.nan if v is None else v for v in row] for row in data["probability"]],
                dtype=float,
            ),
            valid_n=np.array(data["valid_n"], dtype=int),
            binary=np.array([[ch == "1" for ch in row] for row in data["binary"]], dtype=bool),
            binarization=data.get("binarization", {}),
            provenance=data.get("provenance", {}),
            name=data.get("name", ""),
        )


__all__ = ["FORMAT", "StructureExport"]
