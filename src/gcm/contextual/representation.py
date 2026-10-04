"""How a scenario becomes text.

The same content (the description of the organization, the statements about how it works, the
row entities and the opportunities) is rendered in several formats. The formats differ in form
only, never in content, so that differences between the resulting structures can be attributed to
the representation (the "representational format" dimension of the TRAILS robustness audit,
Ye et al. 2026).

``prose``
    A narrative in plain paragraphs.
``role_list``
    A structured list with headings and bullet points.
``statute``
    Numbered sections and clauses in the style of a statute.

Two switches act on every format: ``show_importance`` adds the rank of each entity (default off,
so that the hierarchy has to emerge from the context instead of being given), and ``item_order``
lists the entities in canonical (importance) order or in a shuffled order.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from gcm.contextual.scenario import Entity, Scenario

REPRESENTATIONS = ("prose", "role_list", "statute")
ITEM_ORDERS = ("canonical", "shuffled")

_TEXT = {
    "en": {
        "organization": "Organization",
        "provisions": "How the organization works",
        "statute_provisions": "Provisions",
        "level": "Level in the organization: rank {rank} of {n} (rank 1 is the highest).",
        "importance": "Importance: rank {rank} of {n} (rank 1 is the most important).",
        "prose_rows": "The organization has the following {plural}.",
        "prose_cols": "The following {plural} exist.",
    },
    "de": {
        "organization": "Organisation",
        "provisions": "Arbeitsweise der Organisation",
        "statute_provisions": "Bestimmungen",
        "level": "Ebene in der Organisation: Rang {rank} von {n} (Rang 1 ist der höchste).",
        "importance": "Wichtigkeit: Rang {rank} von {n} (Rang 1 ist der wichtigste).",
        "prose_rows": "Die Organisation hat die folgenden {plural}.",
        "prose_cols": "Es gibt die folgenden {plural}.",
    },
}

# The templates of the three formats. Placeholders in braces are filled by :func:`render`;
# ``{row_items}``, ``{col_items}`` and ``{statement_items}`` are themselves built from the item
# templates below.
TEMPLATES = {
    "prose": (
        "{organization} {statement_items}\n\n{prose_rows} {row_items}\n\n{prose_cols} {col_items}"
    ),
    "role_list": (
        "{organization_heading}\n{organization}\n\n"
        "{row_heading}\n{row_items}\n\n"
        "{col_heading}\n{col_items}\n\n"
        "{provisions_heading}\n{statement_items}"
    ),
    "statute": (
        "§ 1 {organization_heading}\n{organization}\n\n"
        "§ 2 {row_heading}\n{row_items}\n\n"
        "§ 3 {col_heading}\n{col_items}\n\n"
        "§ 4 {provisions_heading}\n{statement_items}"
    ),
}
ITEM_TEMPLATES = {
    "prose": {
        "entity": "{label} {description}.{rank_note}",
        "statement": "{statement}",
        "join": " ",
    },
    "role_list": {
        "entity": "- {label}: {description}.{rank_note}",
        "statement": "- {statement}",
        "join": "\n",
    },
    "statute": {
        "entity": "({number}) {label}: {description}.{rank_note}",
        "statement": "({number}) {statement}",
        "join": "\n",
    },
}


@dataclass(frozen=True)
class ItemOrder:
    """The order in which rows and opportunities are listed (indices into the scenario)."""

    rows: tuple[int, ...]
    cols: tuple[int, ...]


def item_order(scenario: Scenario, mode: str = "canonical", seed: int | str = 0) -> ItemOrder:
    """Canonical (importance) order or a seeded shuffle of both lists."""
    n_rows, n_cols = scenario.shape
    rows, cols = list(range(n_rows)), list(range(n_cols))
    if mode == "shuffled":
        rng = random.Random(f"gcm-item-order-{seed}")
        rng.shuffle(rows)
        rng.shuffle(cols)
    elif mode != "canonical":
        raise ValueError(f"item order must be one of {ITEM_ORDERS}")
    return ItemOrder(tuple(rows), tuple(cols))


def _entity_items(
    entities: tuple[Entity, ...],
    order: tuple[int, ...],
    variant: str,
    language: str,
    rank_text: str | None,
) -> str:
    template = ITEM_TEMPLATES[variant]
    items = []
    for number, index in enumerate(order, start=1):
        e = entities[index]
        note = "" if rank_text is None else " " + rank_text.format(rank=e.rank, n=len(entities))
        items.append(
            template["entity"].format(
                number=number,
                label=capitalize(e.label[language]),
                description=e.description[language],
                rank_note=note,
            )
        )
    return template["join"].join(items)


def capitalize(text: str) -> str:
    """Upper-case the first character only (labels start with an article)."""
    return text[:1].upper() + text[1:]


def entity_sentence(entity: Entity, language: str) -> str:
    """Label and description as one sentence, e.g. for the persona of a participant."""
    return f"{capitalize(entity.label[language])} {entity.description[language]}."


def render(
    scenario: Scenario,
    variant: str = "prose",
    language: str = "en",
    *,
    show_importance: bool = False,
    order: ItemOrder | None = None,
) -> str:
    """Render the description of the organization (the ``{organization_description}`` of the
    query templates)."""
    if variant not in REPRESENTATIONS:
        raise ValueError(f"representation must be one of {REPRESENTATIONS}")
    if language not in scenario.languages:
        raise ValueError(f"scenario {scenario.id} has no texts in language {language!r}")
    order = order or item_order(scenario)
    text = _TEXT[language]
    items = ITEM_TEMPLATES[variant]
    statements = items["join"].join(
        items["statement"].format(number=n, statement=s[language])
        for n, s in enumerate(scenario.statements, start=1)
    )
    row_plural = scenario.term(scenario.row_entity, "plural", language)
    col_plural = scenario.term("opportunity", "plural", language)
    # inside a sentence English nouns are lower case, German nouns keep their capital
    in_sentence = (lambda s: s.lower()) if language == "en" else (lambda s: s)
    return (
        TEMPLATES[variant]
        .format(
            organization=scenario.organization[language],
            organization_heading=text["organization"],
            provisions_heading=text["statute_provisions" if variant == "statute" else "provisions"],
            row_heading=row_plural,
            col_heading=col_plural,
            prose_rows=text["prose_rows"].format(plural=in_sentence(row_plural)),
            prose_cols=text["prose_cols"].format(plural=in_sentence(col_plural)),
            row_items=_entity_items(
                scenario.rows,
                order.rows,
                variant,
                language,
                text["level"] if show_importance else None,
            ),
            col_items=_entity_items(
                scenario.opportunities,
                order.cols,
                variant,
                language,
                text["importance"] if show_importance else None,
            ),
            statement_items=statements,
        )
        .strip()
    )


__all__ = [
    "ITEM_ORDERS",
    "ITEM_TEMPLATES",
    "REPRESENTATIONS",
    "TEMPLATES",
    "ItemOrder",
    "capitalize",
    "entity_sentence",
    "item_order",
    "render",
]
