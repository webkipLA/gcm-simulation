"""From raw model text to eligibility answers.

An answer is valid only if it is a JSON object with a boolean ``eligible`` (per opportunity in
the ``per_row`` mode). Everything else is *invalid*. Invalid answers are counted and reported;
they are never replaced by a default.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class CellAnswer:
    """The answer for one (row, opportunity) cell from one call."""

    col_id: str
    eligible: bool | None  # None = invalid
    reason: str | None = None
    problem: str | None = None  # why the answer is invalid

    @property
    def valid(self) -> bool:
        return self.eligible is not None


def extract_json(text: str) -> dict | None:
    """The first JSON object in ``text``, tolerating code fences and surrounding prose."""
    if not text:
        return None
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            value, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = text.find("{", start + 1)
    return None


def _cell(col_id: str, item) -> CellAnswer:
    if not isinstance(item, dict):
        return CellAnswer(col_id, None, problem="not a JSON object")
    eligible = item.get("eligible")
    if not isinstance(eligible, bool):
        return CellAnswer(col_id, None, problem="eligible is not a boolean")
    reason = item.get("reason")
    return CellAnswer(col_id, eligible, reason=reason if isinstance(reason, str) else None)


def interpret(parsed: dict | None, mode: str, col_ids: tuple[str, ...]) -> list[CellAnswer]:
    """One :class:`CellAnswer` per requested opportunity, valid or invalid."""
    if parsed is None:
        return [CellAnswer(c, None, problem="no JSON object") for c in col_ids]
    if mode == "pairwise":
        return [_cell(col_ids[0], parsed)]
    answers = parsed.get("answers")
    if not isinstance(answers, list):
        return [CellAnswer(c, None, problem="answers is not a list") for c in col_ids]
    by_id: dict[str, list] = {}
    for item in answers:
        if isinstance(item, dict) and isinstance(item.get("opportunity"), str):
            by_id.setdefault(item["opportunity"].strip().strip("[]"), []).append(item)
    out = []
    for c in col_ids:
        items = by_id.get(c, [])
        if not items:
            out.append(CellAnswer(c, None, problem="opportunity missing in the answer"))
        elif len(items) > 1:
            out.append(CellAnswer(c, None, problem="opportunity answered more than once"))
        else:
            out.append(_cell(c, items[0]))
    return out


__all__ = ["CellAnswer", "extract_json", "interpret"]
