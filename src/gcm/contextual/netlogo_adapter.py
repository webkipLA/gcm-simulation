"""The exported structure as a component of the NetLogo port.

The agent-based model has 100 participants and 100 opportunities per default. Asking a language
model about every pair would take 10 000 questions per loop, so the structure is queried for a
small matrix of *roles* × *opportunity types* and expanded to agents through a
:class:`RoleAssignment`:

* every participant gets one role, every opportunity one type;
* the most important type takes the lowest ``who`` numbers (``who`` is the importance rank of
  an opportunity in the NetLogo code, lower = more important), the next type the next block,
  and so on, so the pyramid of ``assign-importance`` and the types agree;
* how roles map onto the abilities drawn at setup is a modeling decision with three settings:
  ``random`` (roles are independent of ability), ``ranked`` (the most important role gets the
  ablest participants) and ``inverse`` (the reverse). With ``ranked`` and ``inverse`` a
  contextual structure can be compared with the rule-based competent and incompetent
  hierarchies, which are defined through ability.

The component implements both ``*_may_enter`` methods of
``gcm.netlogo.interfaces.DecisionStructure`` by a lookup in the role × type matrix. It binds to
the model on first use (it needs the realized abilities), uses its own random generator for the
assignment and never touches the model's generator, so a run with the all-ones matrix is
identical to the unrestricted baseline under the same seed.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from gcm.contextual.structure_io import StructureExport
from gcm.netlogo.agents import Opportunity, Participant, PatchAgents

if TYPE_CHECKING:  # pragma: no cover
    from gcm.netlogo.model import GarbageCanABM

ABILITY_MAPPINGS = ("random", "ranked", "inverse")
MODES = ("threshold", "sample")


def split_counts(n: int, k: int, weights: Sequence[float] | None = None) -> tuple[int, ...]:
    """Split ``n`` agents into ``k`` blocks.

    ``weights`` may be integer counts (must sum to ``n``) or shares (summing to 1); without
    weights the split is as equal as possible, the remainder going to the first blocks. Shares
    are rounded with the largest-remainder method so the counts sum to ``n``.
    """
    if k < 1:
        raise ValueError("at least one block is needed")
    if weights is None:
        base, rest = divmod(n, k)
        return tuple(base + (1 if i < rest else 0) for i in range(k))
    if len(weights) != k:
        raise ValueError(f"expected {k} weights, got {len(weights)}")
    if all(float(w).is_integer() for w in weights) and sum(weights) == n:
        return tuple(int(w) for w in weights)
    total = float(sum(weights))
    if total <= 0:
        raise ValueError("weights must be positive")
    raw = [n * float(w) / total for w in weights]
    counts = [int(x) for x in raw]
    for i in sorted(range(k), key=lambda i: raw[i] - counts[i], reverse=True)[: n - sum(counts)]:
        counts[i] += 1
    return tuple(counts)


@dataclass(frozen=True)
class RoleAssignment:
    """How roles and opportunity types of an export are expanded to agents."""

    role_ids: tuple[str, ...]
    type_ids: tuple[str, ...]
    agents_per_role: tuple[float, ...] | None = None  # counts or shares; None = equal
    opportunities_per_type: tuple[float, ...] | None = None
    ability_mapping: str = "random"
    seed: int = 0

    def __post_init__(self) -> None:
        if self.ability_mapping not in ABILITY_MAPPINGS:
            raise ValueError(f"ability_mapping must be one of {ABILITY_MAPPINGS}")
        if self.agents_per_role is not None and len(self.agents_per_role) != len(self.role_ids):
            raise ValueError("agents_per_role needs one entry per role")
        if self.opportunities_per_type is not None and len(self.opportunities_per_type) != len(
            self.type_ids
        ):
            raise ValueError("opportunities_per_type needs one entry per type")

    @classmethod
    def for_export(cls, export: StructureExport, **overrides) -> RoleAssignment:
        """Defaults for an export, overridden by the scenario's ``assignment`` block or by
        keyword arguments (``agents_per_role``, ``opportunities_per_type``, ``ability_mapping``,
        ``seed``)."""
        values: dict = {}
        for key in ("agents_per_role", "opportunities_per_type"):
            if overrides.get(key) is not None:
                values[key] = tuple(overrides[key])
        for key in ("ability_mapping", "seed"):
            if overrides.get(key) is not None:
                values[key] = overrides[key]
        return cls(export.row_ids, export.col_ids, **values)

    def with_(self, **changes) -> RoleAssignment:
        return replace(self, **changes)

    # ------------------------------------------------------------------ expansion
    def role_counts(self, n_participants: int) -> tuple[int, ...]:
        return split_counts(n_participants, len(self.role_ids), self.agents_per_role)

    def type_counts(self, n_opportunities: int) -> tuple[int, ...]:
        return split_counts(n_opportunities, len(self.type_ids), self.opportunities_per_type)

    def participant_roles(self, participants: Sequence[Participant]) -> dict[int, int]:
        """``who`` → role index. Blocks follow the chosen ability mapping."""
        agents = list(participants)
        if self.ability_mapping == "random":
            random.Random(f"gcm-role-assignment-{self.seed}").shuffle(agents)
        elif self.ability_mapping == "ranked":
            agents.sort(key=lambda a: (-a.ability, a.who))
        else:
            agents.sort(key=lambda a: (a.ability, a.who))
        out: dict[int, int] = {}
        start = 0
        for role, count in enumerate(self.role_counts(len(agents))):
            for a in agents[start : start + count]:
                out[a.who] = role
            start += count
        return out

    def opportunity_types(self, opportunities: Sequence[Opportunity]) -> dict[int, int]:
        """``who`` → type index. The most important type takes the lowest ``who`` numbers."""
        ordered = sorted(opportunities, key=lambda o: o.who)
        out: dict[int, int] = {}
        start = 0
        for kind, count in enumerate(self.type_counts(len(ordered))):
            for o in ordered[start : start + count]:
                out[o.who] = kind
            start += count
        return out


class ContextualNetLogoDecisionStructure:
    """``DecisionStructure`` of the NetLogo port backed by a role × type export."""

    def __init__(
        self,
        export: StructureExport,
        assignment: RoleAssignment | None = None,
        *,
        mode: str = "threshold",
        seed: int | None = None,
    ) -> None:
        if export.row_entity != "participant":
            raise ValueError(
                "the NetLogo decision structure needs a participants × opportunities export"
            )
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.export = export
        self.assignment = assignment or RoleAssignment.for_export(export)
        if self.assignment.role_ids != export.row_ids or self.assignment.type_ids != export.col_ids:
            raise ValueError("the assignment does not match the roles and types of the export")
        self.mode, self.seed = mode, seed
        if mode == "threshold":
            self.permitted = export.binary.copy()
        else:
            self.permitted = export.sample(np.random.default_rng(seed))
        suffix = mode + (f"@{seed}" if mode == "sample" else "")
        self.name = f"contextual:{export.name}:{self.assignment.ability_mapping}:{suffix}"
        self._bound_to: GarbageCanABM | None = None
        self._role: dict[int, int] = {}
        self._type: dict[int, int] = {}

    # ------------------------------------------------------------------ binding
    def bind(self, model: GarbageCanABM) -> None:
        """Assign roles and types for the agents of ``model`` (done once, on first use)."""
        self._role = self.assignment.participant_roles(model.participants)
        self._type = self.assignment.opportunity_types(model.opportunities)
        self._bound_to = model

    def _ensure(self, model: GarbageCanABM) -> None:
        if self._bound_to is not model:
            self.bind(model)

    def role_of(self, participant: Participant) -> int:
        return self._role[participant.who]

    def type_of(self, opportunity: Opportunity) -> int:
        return self._type[opportunity.who]

    def assignment_table(self, model: GarbageCanABM) -> pd.DataFrame:
        """Roles with their agent counts and ability statistics (for display)."""
        self._ensure(model)
        rows = []
        for r, role in enumerate(self.assignment.role_ids):
            abilities = [a.ability for a in model.participants if self._role[a.who] == r]
            rows.append(
                {
                    "role": role,
                    "participants": len(abilities),
                    "mean_ability": float(np.mean(abilities)) if abilities else float("nan"),
                    "min_ability": min(abilities) if abilities else float("nan"),
                    "max_ability": max(abilities) if abilities else float("nan"),
                    "permitted_types": [
                        t for t, kind in enumerate(self.assignment.type_ids) if self.permitted[r, t]
                    ],
                }
            )
        return pd.DataFrame(rows)

    def type_table(self, model: GarbageCanABM) -> pd.DataFrame:
        self._ensure(model)
        rows = []
        for t, kind in enumerate(self.assignment.type_ids):
            whos = sorted(o.who for o in model.opportunities if self._type[o.who] == t)
            rows.append(
                {
                    "type": kind,
                    "opportunities": len(whos),
                    "who_from": whos[0] if whos else None,
                    "who_to": whos[-1] if whos else None,
                    "high_importance": sum(w <= model.hierarchy_divide for w in whos),
                }
            )
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------ the Protocol
    def participant_may_enter(
        self, participant: Participant, target: PatchAgents, model: GarbageCanABM
    ) -> bool:
        if not target.opportunities:
            return True
        self._ensure(model)
        row = self.permitted[self._role[participant.who]]
        return all(row[self._type[o.who]] for o in target.opportunities)

    def opportunity_may_enter(
        self, opportunity: Opportunity, target: PatchAgents, model: GarbageCanABM
    ) -> bool:
        if not target.participants:
            return True
        self._ensure(model)
        column = self.permitted[:, self._type[opportunity.who]]
        return all(column[self._role[a.who]] for a in target.participants)


def rule_based_as_export(model: GarbageCanABM, structure) -> tuple[StructureExport, RoleAssignment]:
    """The rule-based decision structure of ``model`` as a 2 × 2 role × type export.

    Roles: participants above and up to the ability threshold; types: high- and low-importance
    opportunities (``who <= hierarchy_divide``). Used to check that the contextual component
    reproduces the rule-based hierarchies exactly.
    """
    from gcm.netlogo.parameters import Structure

    p = model.params
    n_high = sum(a.ability > p.ability_threshold for a in model.participants)
    n_important = sum(o.who <= model.hierarchy_divide for o in model.opportunities)
    if structure is Structure.COMPETENT_HIERARCHY:
        binary = np.array([[True, False], [False, True]])
    elif structure is Structure.INCOMPETENT_HIERARCHY:
        binary = np.array([[False, True], [True, False]])
    else:
        binary = np.ones((2, 2), dtype=bool)
    export = StructureExport(
        scenario_id=f"rule_based_{structure.name.lower()}",
        row_entity="participant",
        row_ids=("high_ability", "low_ability"),
        col_ids=("important", "unimportant"),
        row_labels=("participants above the ability threshold", "participants at or below it"),
        col_labels=("high-importance opportunities", "low-importance opportunities"),
        probability=binary.astype(float),
        valid_n=np.zeros((2, 2), dtype=int),
        binary=binary,
        binarization={"mode": "given"},
        provenance={"source": f"rule-based {structure.value}"},
        name=f"rule_based_{structure.name.lower()}",
    )
    assignment = RoleAssignment(
        export.row_ids,
        export.col_ids,
        agents_per_role=(n_high, len(model.participants) - n_high),
        opportunities_per_type=(n_important, len(model.opportunities) - n_important),
        ability_mapping="ranked",
    )
    return export, assignment


__all__ = [
    "ABILITY_MAPPINGS",
    "MODES",
    "ContextualNetLogoDecisionStructure",
    "RoleAssignment",
    "rule_based_as_export",
    "split_counts",
]
