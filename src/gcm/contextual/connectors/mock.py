"""A connector without a model: it answers from a target matrix, with configurable noise.

Used by every test and by the notebook when no API is configured. The answers are a deterministic
function of the mock's seed and the request (row, opportunity, loop, call seed), so results do
not depend on thread scheduling and can be reproduced exactly.
"""

from __future__ import annotations

import hashlib
import json
import random

import numpy as np

from gcm.contextual.connectors.base import BaseConnector, ConnectorError, ConnectorLimits


class MockConnector(BaseConnector):
    """Answers ``target[row, opportunity]``, flipped with probability ``noise``.

    With probability ``invalid_rate`` a call returns text that is not a valid answer, which
    exercises the handling of invalid answers.
    """

    name = "mock"

    def __init__(
        self,
        target: np.ndarray,
        row_ids: tuple[str, ...],
        col_ids: tuple[str, ...],
        *,
        noise: float = 0.0,
        invalid_rate: float = 0.0,
        seed: int = 0,
        model: str = "mock",
        limits: ConnectorLimits | None = None,
    ) -> None:
        super().__init__(model, limits or ConnectorLimits(max_concurrency=8, max_retries=0))
        target = np.asarray(target, dtype=bool)
        if target.shape != (len(row_ids), len(col_ids)):
            raise ValueError("the target matrix must be rows × opportunities")
        if not (0.0 <= noise <= 1.0 and 0.0 <= invalid_rate <= 1.0):
            raise ValueError("noise and invalid_rate are probabilities")
        self.target = target
        self.noise, self.invalid_rate, self.seed = float(noise), float(invalid_rate), int(seed)
        self._row = {r: i for i, r in enumerate(row_ids)}
        self._col = {c: i for i, c in enumerate(col_ids)}

    @classmethod
    def for_scenario(cls, scenario, target: np.ndarray | None = None, **kwargs) -> MockConnector:
        """A mock for ``scenario``; the target defaults to the scenario's expected matrix."""
        if target is None:
            target = scenario.target_matrix()
        if target is None:
            raise ValueError(f"scenario {scenario.id} has no expected structure; pass a target")
        return cls(target, scenario.row_ids, scenario.col_ids, **kwargs)

    def identity(self) -> dict:
        digest = hashlib.sha256(np.packbits(self.target).tobytes()).hexdigest()[:12]
        return {
            "connector": self.name,
            "model": self.model,
            "noise": self.noise,
            "invalid_rate": self.invalid_rate,
            "seed": self.seed,
            "target": f"{self.target.shape[0]}x{self.target.shape[1]}:{digest}",
        }

    def _call(self, system, user, temperature, seed, schema, meta):
        if not meta or "row_id" not in meta or "col_ids" not in meta:
            raise ConnectorError("the Mock connector needs the request coordinates in meta")
        with_reason = schema is None or "reason" in json.dumps(schema)
        row = self._row[meta["row_id"]]
        loop = meta.get("loop", 0)
        model_id = f"{self.model}(noise={self.noise:g})"
        answers = []
        for col_id in meta["col_ids"]:
            rng = random.Random(f"gcm-mock|{self.seed}|{meta['row_id']}|{col_id}|{loop}|{seed}")
            if rng.random() < self.invalid_rate:
                return "I am not able to answer this question.", model_id, None
            eligible = bool(self.target[row, self._col[col_id]])
            if rng.random() < self.noise:
                eligible = not eligible
            answer: dict = {"opportunity": col_id}
            if with_reason:
                answer["reason"] = "Mock answer from the target matrix."
            answer["eligible"] = eligible
            answers.append(answer)
        if meta.get("mode", "pairwise") == "pairwise":
            answers[0].pop("opportunity")
            return json.dumps(answers[0]), model_id, None
        return json.dumps({"answers": answers}), model_id, None


__all__ = ["MockConnector"]
