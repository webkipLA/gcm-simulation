"""Scenario descriptions as data files.

A scenario describes one organization in natural language: who takes part (the *row entities*,
participants for the decision structure), which decision opportunities exist, and what is known
about how the organization works. Scenarios are YAML files, not code. The order of the
participants and of the opportunities in the file is their importance order (first = most
important). That order is a modeling decision: it fixes the matrix indices, and with them the
energy of each participant in the unequal energy distributions of the FORTRAN port, the entry
period of each opportunity and the tie-breaking of the allocation rules. Every entity therefore
carries an explicit ``rank`` that must agree with its position.

One file may define several *variants* that share the entities and differ in the statements
about the organization. Each variant becomes its own :class:`Scenario` with the id
``<file id>_<variant id>``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from gcm.common import StructureKind

LANGUAGES = ("en", "de")
KINDS = ("reference", "placeholder", "custom")
_ID = re.compile(r"^[a-z0-9_]+$")

DEFAULT_TERMS: dict[str, dict[str, dict[str, str]]] = {
    "participant": {
        "singular": {"en": "Person", "de": "Person"},
        "plural": {"en": "Members", "de": "Mitglieder"},
    },
    "problem": {
        "singular": {"en": "Issue", "de": "Anliegen"},
        "plural": {"en": "Issues", "de": "Anliegen"},
    },
    "opportunity": {
        "singular": {"en": "Decision occasion", "de": "Entscheidungsgelegenheit"},
        "plural": {"en": "Decision occasions", "de": "Entscheidungsgelegenheiten"},
    },
}


class ScenarioError(ValueError):
    """A scenario file is malformed."""


@dataclass(frozen=True)
class Entity:
    """One participant (or problem) or one opportunity.

    ``label`` names the entity with its article ("the dean"); ``description`` is a predicate
    without subject and without final period ("heads a faculty"), so that label and description
    together form one sentence in every representation.
    """

    id: str
    label: Mapping[str, str]
    description: Mapping[str, str]
    rank: int  # 1 = most important; equals the 1-based position in the scenario


@dataclass(frozen=True)
class Scenario:
    """One organization described in natural language."""

    id: str
    kind: str
    title: Mapping[str, str]
    row_entity: str
    rows: tuple[Entity, ...]
    opportunities: tuple[Entity, ...]
    organization: Mapping[str, str]
    statements: tuple[Mapping[str, str], ...]
    languages: tuple[str, ...] = LANGUAGES
    terms: Mapping[str, Mapping[str, Mapping[str, str]]] = field(default_factory=dict)
    expected: str | None = None
    expected_matrix: np.ndarray | None = None
    factors: Mapping[str, str] = field(default_factory=dict)
    assignment: Mapping | None = None
    notes: str = ""
    source: str = ""

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.rows), len(self.opportunities)

    @property
    def row_ids(self) -> tuple[str, ...]:
        return tuple(e.id for e in self.rows)

    @property
    def col_ids(self) -> tuple[str, ...]:
        return tuple(e.id for e in self.opportunities)

    def row_labels(self, language: str) -> tuple[str, ...]:
        return tuple(e.label[language] for e in self.rows)

    def col_labels(self, language: str) -> tuple[str, ...]:
        return tuple(e.label[language] for e in self.opportunities)

    def term(self, entity: str, number: str, language: str) -> str:
        """How an entity kind is called in text, e.g. ``term("opportunity", "plural", "de")``."""
        own = self.terms.get(entity, {}).get(number, {})
        if language in own:
            return own[language]
        return DEFAULT_TERMS[entity][number][language]

    def target_matrix(self) -> np.ndarray | None:
        """The matrix this scenario is expected to yield, if the theory makes a statement.

        Used for validation and for the Mock connector only. It is never rendered into a prompt.
        """
        if self.expected_matrix is not None:
            return self.expected_matrix
        if self.expected is not None:
            from gcm.contextual.references import reference_matrix

            return reference_matrix(self.expected, *self.shape)
        return None


# ------------------------------------------------------------------------------------- loading
def default_scenario_dir() -> Path:
    """The scenarios shipped with the package."""
    return Path(__file__).parent / "scenarios"


def _texts(value, languages: tuple[str, ...], where: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ScenarioError(f"{where}: expected a mapping language → text, got {value!r}")
    missing = [lang for lang in languages if not str(value.get(lang, "")).strip()]
    if missing:
        raise ScenarioError(f"{where}: missing text for language(s) {missing}")
    return {lang: " ".join(str(value[lang]).split()) for lang in languages}


def _entities(items, languages: tuple[str, ...], where: str) -> tuple[Entity, ...]:
    if not isinstance(items, list) or not items:
        raise ScenarioError(f"{where}: expected a non-empty list")
    out = []
    for pos, item in enumerate(items, start=1):
        here = f"{where}[{pos}]"
        if not isinstance(item, Mapping) or "id" not in item:
            raise ScenarioError(f"{here}: every entry needs an id")
        eid = str(item["id"])
        if not _ID.match(eid):
            raise ScenarioError(f"{here}: id {eid!r} must match [a-z0-9_]+")
        rank = item.get("rank", pos)
        if rank != pos:
            raise ScenarioError(
                f"{here}: rank {rank} contradicts position {pos}; the order of the list is the "
                "importance order, so reorder the list instead of changing the rank"
            )
        out.append(
            Entity(
                id=eid,
                label=_texts(item.get("label"), languages, f"{here}.label"),
                description={
                    lang: text.rstrip(". ")
                    for lang, text in _texts(
                        item.get("description"), languages, f"{here}.description"
                    ).items()
                },
                rank=pos,
            )
        )
    ids = [e.id for e in out]
    if len(set(ids)) != len(ids):
        raise ScenarioError(f"{where}: ids must be unique")
    return tuple(out)


def _matrix(rows, shape: tuple[int, int], where: str) -> np.ndarray:
    if not isinstance(rows, list) or len(rows) != shape[0]:
        raise ScenarioError(f"{where}: expected {shape[0]} rows")
    out = np.zeros(shape, dtype=bool)
    for r, row in enumerate(rows):
        text = str(row)
        if len(text) != shape[1] or set(text) - {"0", "1"}:
            raise ScenarioError(f"{where}[{r + 1}]: expected {shape[1]} characters 0/1")
        out[r] = [ch == "1" for ch in text]
    return out


def _build(base: Mapping, variant: Mapping | None, source: str) -> Scenario:
    where = source
    base_id = str(base.get("id", ""))
    if not _ID.match(base_id):
        raise ScenarioError(f"{where}: id {base_id!r} must match [a-z0-9_]+")
    languages = tuple(base.get("languages", LANGUAGES))
    if not languages or set(languages) - set(LANGUAGES):
        raise ScenarioError(f"{where}: languages must be a subset of {LANGUAGES}")
    kind = base.get("kind", "custom")
    if kind not in KINDS:
        raise ScenarioError(f"{where}: kind must be one of {KINDS}")
    row_entity = base.get("row_entity", "participant")
    if row_entity not in ("participant", "problem"):
        raise ScenarioError(f"{where}: row_entity must be 'participant' or 'problem'")
    row_key = "rows" if "rows" in base else f"{row_entity}s"
    rows = _entities(base.get(row_key), languages, f"{where}:{row_key}")
    opportunities = _entities(base.get("opportunities"), languages, f"{where}:opportunities")
    shape = (len(rows), len(opportunities))

    merged = dict(base)
    sid = base_id
    statements = list(base.get("statements") or [])
    if variant is not None:
        vid = str(variant.get("id", ""))
        if not _ID.match(vid):
            raise ScenarioError(f"{where}: variant id {vid!r} must match [a-z0-9_]+")
        sid = f"{base_id}_{vid}"
        where = f"{source}:{vid}"
        statements += list(variant.get("statements") or [])
        for key in ("title", "organization", "expected", "expected_matrix", "factors", "notes"):
            if key in variant:
                merged[key] = variant[key]

    expected = merged.get("expected")
    if expected is not None:
        try:
            expected = StructureKind(expected).value
        except ValueError as exc:
            raise ScenarioError(f"{where}: unknown expected structure {expected!r}") from exc
    expected_matrix = None
    if merged.get("expected_matrix") is not None:
        expected_matrix = _matrix(merged["expected_matrix"], shape, f"{where}:expected_matrix")
    terms = {}
    for entity, numbers in (merged.get("terms") or {}).items():
        key = "opportunity" if entity == "opportunity" else row_entity
        terms[key] = {
            number: _texts(texts, languages, f"{where}:terms.{entity}.{number}")
            for number, texts in numbers.items()
        }
    return Scenario(
        id=sid,
        kind=kind,
        title=_texts(merged.get("title"), languages, f"{where}:title"),
        row_entity=row_entity,
        rows=rows,
        opportunities=opportunities,
        organization=_texts(merged.get("organization"), languages, f"{where}:organization"),
        statements=tuple(
            _texts(s, languages, f"{where}:statements[{i + 1}]") for i, s in enumerate(statements)
        ),
        languages=languages,
        terms=terms,
        expected=expected,
        expected_matrix=expected_matrix,
        factors=dict(merged.get("factors") or {}),
        assignment=merged.get("assignment"),
        notes=" ".join(str(merged.get("notes", "")).split()),
        source=source,
    )


def load_scenario_file(path: str | Path) -> list[Scenario]:
    """Load one YAML file. A file with ``variants`` yields one scenario per variant."""
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, Mapping):
        raise ScenarioError(f"{path.name}: the file must contain a mapping")
    variants = data.get("variants")
    if not variants:
        return [_build(data, None, path.name)]
    return [_build(data, v, path.name) for v in variants]


def load_scenarios(directory: str | Path | None = None) -> dict[str, Scenario]:
    """All scenarios of a directory (default: the ones shipped with the package), by id."""
    directory = Path(directory) if directory is not None else default_scenario_dir()
    out: dict[str, Scenario] = {}
    for path in sorted(directory.glob("*.y*ml")):
        for scenario in load_scenario_file(path):
            if scenario.id in out:
                raise ScenarioError(f"{path.name}: duplicate scenario id {scenario.id!r}")
            out[scenario.id] = scenario
    return out


__all__ = [
    "DEFAULT_TERMS",
    "LANGUAGES",
    "Entity",
    "Scenario",
    "ScenarioError",
    "default_scenario_dir",
    "load_scenario_file",
    "load_scenarios",
]
