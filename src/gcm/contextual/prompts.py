"""The query syntax: system and user templates, the expected JSON answer and its schema.

The LLM is asked one narrow question: is this row entity *permitted* to enter this opportunity?
It never decides whether a participant would want to attend; that behaviour stays in the
rule-based core of the simulations. The templates never mention the theory behind the experiment.
:func:`find_banned_terms` enforces this for every prompt that is built, so that answers come from
the described context and not from memorized theory.

Factors of the robustness audit that live here:

``wording``      two paraphrases of the same instruction ("a", "b");
``perspective``  a neutral observer or a first-person persona of the participant;
``language``     English or German;
``mode``         one call per (row, opportunity) pair, or one call per row listing all
                 opportunities;
``with_reason``  whether the answer carries a short reason before the verdict.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

WORDINGS = ("a", "b")
PERSPECTIVES = ("observer", "persona")
MODES = ("pairwise", "per_row")
PLACEHOLDERS = (
    "organization_description",
    "participant",
    "participant_description",
    "opportunity",
    "opportunity_list",
    "answer_format",
)

# ------------------------------------------------------------------------- guard against leaks
BANNED_PATTERNS = (
    r"garbage[\s-]*can",
    r"mülleimer",
    r"anarch",
    r"unsegment",
    r"hierarch",
    r"speciali[sz]ed",
    r"spezialisiert",
    r"\bcohen\b",
    r"\bolsen\b",
    r"fioretti",
)
_BANNED = re.compile("|".join(f"(?:{p})" for p in BANNED_PATTERNS), re.IGNORECASE)


class PromptLeakError(ValueError):
    """A prompt would mention the theory or one of the structure names."""


def find_banned_terms(text: str) -> list[str]:
    """Theory terms and structure names found in ``text`` (empty list = clean)."""
    return sorted({m.group(0).lower() for m in _BANNED.finditer(text)})


# ----------------------------------------------------------------------------------- templates
# Keyed by language → row entity → perspective → wording. "problem" is provided so that the
# access structure (problems × opportunities) can reuse the pipeline later; a problem has no
# first-person perspective.
SYSTEM_TEMPLATES = {
    "en": {
        "participant": {
            "observer": {
                "a": (
                    "You assess formal participation rights in an organization. You receive a "
                    "description of the organization and one question. Judge only whether the "
                    "person is permitted to take part. Do not judge whether the person would "
                    "want to attend, has the time or would be useful there. Rely only on the "
                    "description. If the description does not settle the matter explicitly, "
                    "give the most plausible reading of it. Reply with one JSON object and "
                    "nothing else, in this form: {answer_format}"
                ),
                "b": (
                    "Your task is to determine who is entitled to attend which decision "
                    "occasion in an organization. Below you find a description of the "
                    "organization, followed by a question. Decide only whether the person has "
                    "the right to participate. Whether the person is interested, available or "
                    "helpful is irrelevant. Use nothing but the description. Where the "
                    "description leaves the matter open, choose the reading that fits it best. "
                    "Answer with a single JSON object of this form and add nothing else: "
                    "{answer_format}"
                ),
            },
            "persona": {
                "a": (
                    "You are {participant} in the organization described below. "
                    "{participant_description} You receive a description of the organization "
                    "and one question. Judge only whether you are permitted to take part. Do "
                    "not judge whether you would want to attend, have the time or would be "
                    "useful there. Rely only on the description. If the description does not "
                    "settle the matter explicitly, give the most plausible reading of it. "
                    "Reply with one JSON object and nothing else, in this form: {answer_format}"
                ),
                "b": (
                    "In the organization described below, you are {participant}. "
                    "{participant_description} Below you find a description of the "
                    "organization, followed by a question. Decide only whether you have the "
                    "right to participate. Whether you are interested, available or helpful is "
                    "irrelevant. Use nothing but the description. Where the description leaves "
                    "the matter open, choose the reading that fits it best. Answer with a "
                    "single JSON object of this form and add nothing else: {answer_format}"
                ),
            },
        },
        "problem": {
            "observer": {
                "a": (
                    "You assess which issues may be dealt with at which decision occasion in "
                    "an organization. You receive a description of the organization and one "
                    "question. Judge only whether the issue is admitted. Do not judge whether "
                    "it would be solved there. Rely only on the description. If the "
                    "description does not settle the matter explicitly, give the most "
                    "plausible reading of it. Reply with one JSON object and nothing else, in "
                    "this form: {answer_format}"
                ),
                "b": (
                    "Your task is to determine which issues may be raised at which decision "
                    "occasion in an organization. Below you find a description of the "
                    "organization, followed by a question. Decide only whether the issue may "
                    "be brought there. Whether it would be solved there is irrelevant. Use "
                    "nothing but the description. Where the description leaves the matter "
                    "open, choose the reading that fits it best. Answer with a single JSON "
                    "object of this form and add nothing else: {answer_format}"
                ),
            },
        },
    },
    "de": {
        "participant": {
            "observer": {
                "a": (
                    "Sie beurteilen formale Teilnahmerechte in einer Organisation. Sie erhalten "
                    "eine Beschreibung der Organisation und eine Frage. Beurteilen Sie nur, ob "
                    "die Person teilnehmen darf. Beurteilen Sie nicht, ob die Person teilnehmen "
                    "möchte, Zeit hat oder dort nützlich wäre. Stützen Sie sich nur auf die "
                    "Beschreibung. Wenn die Beschreibung die Frage nicht ausdrücklich klärt, "
                    "wählen Sie die plausibelste Lesart. Antworten Sie mit genau einem "
                    "JSON-Objekt und nichts anderem, in dieser Form: {answer_format}"
                ),
                "b": (
                    "Ihre Aufgabe ist es festzustellen, wer in einer Organisation zu welcher "
                    "Entscheidungsgelegenheit zugelassen ist. Unten finden Sie eine "
                    "Beschreibung der Organisation und danach eine Frage. Entscheiden Sie nur, "
                    "ob die Person das Recht zur Teilnahme hat. Ob die Person interessiert, "
                    "verfügbar oder hilfreich ist, spielt keine Rolle. Verwenden Sie "
                    "ausschließlich die Beschreibung. Wo die Beschreibung die Frage offen "
                    "lässt, wählen Sie die Lesart, die am besten zu ihr passt. Antworten Sie "
                    "mit einem einzigen JSON-Objekt dieser Form und fügen Sie nichts hinzu: "
                    "{answer_format}"
                ),
            },
            "persona": {
                "a": (
                    "Sie sind {participant} in der unten beschriebenen Organisation. "
                    "{participant_description} Sie erhalten eine Beschreibung der Organisation "
                    "und eine Frage. Beurteilen Sie nur, ob Sie teilnehmen dürfen. Beurteilen "
                    "Sie nicht, ob Sie teilnehmen möchten, Zeit haben oder dort nützlich wären. "
                    "Stützen Sie sich nur auf die Beschreibung. Wenn die Beschreibung die Frage "
                    "nicht ausdrücklich klärt, wählen Sie die plausibelste Lesart. Antworten "
                    "Sie mit genau einem JSON-Objekt und nichts anderem, in dieser Form: "
                    "{answer_format}"
                ),
                "b": (
                    "In der unten beschriebenen Organisation sind Sie {participant}. "
                    "{participant_description} Unten finden Sie eine Beschreibung der "
                    "Organisation und danach eine Frage. Entscheiden Sie nur, ob Sie das Recht "
                    "zur Teilnahme haben. Ob Sie interessiert, verfügbar oder hilfreich sind, "
                    "spielt keine Rolle. Verwenden Sie ausschließlich die Beschreibung. Wo die "
                    "Beschreibung die Frage offen lässt, wählen Sie die Lesart, die am besten "
                    "zu ihr passt. Antworten Sie mit einem einzigen JSON-Objekt dieser Form "
                    "und fügen Sie nichts hinzu: {answer_format}"
                ),
            },
        },
        "problem": {
            "observer": {
                "a": (
                    "Sie beurteilen, welche Anliegen in einer Organisation bei welcher "
                    "Entscheidungsgelegenheit behandelt werden dürfen. Sie erhalten eine "
                    "Beschreibung der Organisation und eine Frage. Beurteilen Sie nur, ob das "
                    "Anliegen zugelassen ist. Beurteilen Sie nicht, ob es dort gelöst würde. "
                    "Stützen Sie sich nur auf die Beschreibung. Wenn die Beschreibung die Frage "
                    "nicht ausdrücklich klärt, wählen Sie die plausibelste Lesart. Antworten "
                    "Sie mit genau einem JSON-Objekt und nichts anderem, in dieser Form: "
                    "{answer_format}"
                ),
                "b": (
                    "Ihre Aufgabe ist es festzustellen, welche Anliegen in einer Organisation "
                    "bei welcher Entscheidungsgelegenheit eingebracht werden dürfen. Unten "
                    "finden Sie eine Beschreibung der Organisation und danach eine Frage. "
                    "Entscheiden Sie nur, ob das Anliegen dort eingebracht werden darf. Ob es "
                    "dort gelöst würde, spielt keine Rolle. Verwenden Sie ausschließlich die "
                    "Beschreibung. Wo die Beschreibung die Frage offen lässt, wählen Sie die "
                    "Lesart, die am besten zu ihr passt. Antworten Sie mit einem einzigen "
                    "JSON-Objekt dieser Form und fügen Sie nichts hinzu: {answer_format}"
                ),
            },
        },
    },
}

# The user message: description, the pair in question, the question. The labels are set off with
# colons so that the same template works for every label in both languages (German labels would
# otherwise need a different grammatical case inside a sentence).
_USER_HEAD = {
    "en": "Description of the organization:\n{organization_description}\n\n",
    "de": "Beschreibung der Organisation:\n{organization_description}\n\n",
}
_USER_BODY = {
    "en": {
        "participant": {
            "pairwise": "Person: {participant}\nDecision occasion: {opportunity}\n\n",
            "per_row": "Person: {participant}\n\nDecision occasions:\n{opportunity_list}\n\n",
            "pairwise_persona": "Decision occasion: {opportunity}\n\n",
            "per_row_persona": "Decision occasions:\n{opportunity_list}\n\n",
        },
        "problem": {
            "pairwise": "Issue: {participant}\nDecision occasion: {opportunity}\n\n",
            "per_row": "Issue: {participant}\n\nDecision occasions:\n{opportunity_list}\n\n",
        },
    },
    "de": {
        "participant": {
            "pairwise": "Person: {participant}\nEntscheidungsgelegenheit: {opportunity}\n\n",
            "per_row": (
                "Person: {participant}\n\nEntscheidungsgelegenheiten:\n{opportunity_list}\n\n"
            ),
            "pairwise_persona": "Entscheidungsgelegenheit: {opportunity}\n\n",
            "per_row_persona": "Entscheidungsgelegenheiten:\n{opportunity_list}\n\n",
        },
        "problem": {
            "pairwise": "Anliegen: {participant}\nEntscheidungsgelegenheit: {opportunity}\n\n",
            "per_row": (
                "Anliegen: {participant}\n\nEntscheidungsgelegenheiten:\n{opportunity_list}\n\n"
            ),
        },
    },
}
# question by language → row entity → perspective → mode → wording
_QUESTION = {
    "en": {
        "participant": {
            "observer": {
                "pairwise": {
                    "a": "Question: Is this person permitted to take part in this decision "
                    "occasion?",
                    "b": "Question: Does this person have the right to participate in this "
                    "decision occasion?",
                },
                "per_row": {
                    "a": "Question: For each listed decision occasion, is this person "
                    "permitted to take part in it?",
                    "b": "Question: For each listed decision occasion, does this person have "
                    "the right to participate in it?",
                },
            },
            "persona": {
                "pairwise": {
                    "a": "Question: Are you permitted to take part in this decision occasion?",
                    "b": "Question: Do you have the right to participate in this decision "
                    "occasion?",
                },
                "per_row": {
                    "a": "Question: For each listed decision occasion, are you permitted to "
                    "take part in it?",
                    "b": "Question: For each listed decision occasion, do you have the right "
                    "to participate in it?",
                },
            },
        },
        "problem": {
            "observer": {
                "pairwise": {
                    "a": "Question: May this issue be dealt with at this decision occasion?",
                    "b": "Question: May this issue be raised at this decision occasion?",
                },
                "per_row": {
                    "a": "Question: For each listed decision occasion, may this issue be dealt "
                    "with there?",
                    "b": "Question: For each listed decision occasion, may this issue be raised "
                    "there?",
                },
            },
        },
    },
    "de": {
        "participant": {
            "observer": {
                "pairwise": {
                    "a": "Frage: Darf diese Person an dieser Entscheidungsgelegenheit teilnehmen?",
                    "b": "Frage: Hat diese Person das Recht, an dieser "
                    "Entscheidungsgelegenheit mitzuwirken?",
                },
                "per_row": {
                    "a": "Frage: Darf diese Person an der jeweiligen "
                    "Entscheidungsgelegenheit teilnehmen?",
                    "b": "Frage: Hat diese Person das Recht, an der jeweiligen "
                    "Entscheidungsgelegenheit mitzuwirken?",
                },
            },
            "persona": {
                "pairwise": {
                    "a": "Frage: Dürfen Sie an dieser Entscheidungsgelegenheit teilnehmen?",
                    "b": "Frage: Haben Sie das Recht, an dieser Entscheidungsgelegenheit "
                    "mitzuwirken?",
                },
                "per_row": {
                    "a": "Frage: Dürfen Sie an der jeweiligen Entscheidungsgelegenheit teilnehmen?",
                    "b": "Frage: Haben Sie das Recht, an der jeweiligen "
                    "Entscheidungsgelegenheit mitzuwirken?",
                },
            },
        },
        "problem": {
            "observer": {
                "pairwise": {
                    "a": "Frage: Darf dieses Anliegen bei dieser Entscheidungsgelegenheit "
                    "behandelt werden?",
                    "b": "Frage: Darf dieses Anliegen bei dieser Entscheidungsgelegenheit "
                    "eingebracht werden?",
                },
                "per_row": {
                    "a": "Frage: Darf dieses Anliegen bei der jeweiligen "
                    "Entscheidungsgelegenheit behandelt werden?",
                    "b": "Frage: Darf dieses Anliegen bei der jeweiligen "
                    "Entscheidungsgelegenheit eingebracht werden?",
                },
            },
        },
    },
}

_REASON = {"en": "<one short sentence>", "de": "<ein kurzer Satz>"}


@dataclass(frozen=True)
class PromptTemplate:
    """Unfilled system and user templates plus the description of the expected answer."""

    system: str
    user: str
    answer_format: str
    schema: dict

    @property
    def template_hash(self) -> str:
        """Short hash of the unfilled templates (identifies the query syntax in the logs)."""
        blob = "\x1f".join((self.system, self.user, self.answer_format)).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:12]


def answer_format(mode: str, with_reason: bool, language: str) -> str:
    """The JSON answer the model is asked for, as shown in the system message."""
    reason = f'"reason": "{_REASON[language]}", ' if with_reason else ""
    single = "{" + reason + '"eligible": true or false}'
    if mode == "pairwise":
        return single
    item = '{"opportunity": "<id>", ' + reason + '"eligible": true or false}'
    return '{"answers": [' + item + ", ...]}"


def answer_schema(mode: str, with_reason: bool) -> dict:
    """JSON schema of the answer, for providers with a structured output mode.

    ``reason`` comes before ``eligible`` so that the model states its reason before the verdict.
    """
    properties: dict = {}
    if with_reason:
        properties["reason"] = {"type": "string"}
    properties["eligible"] = {"type": "boolean"}
    single = {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
    if mode == "pairwise":
        return single
    item_properties = {"opportunity": {"type": "string"}, **properties}
    item = {
        "type": "object",
        "properties": item_properties,
        "required": list(item_properties),
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"answers": {"type": "array", "items": item}},
        "required": ["answers"],
        "additionalProperties": False,
    }


def get_template(
    *,
    language: str = "en",
    row_entity: str = "participant",
    perspective: str = "observer",
    wording: str = "a",
    mode: str = "pairwise",
    with_reason: bool = True,
) -> PromptTemplate:
    """The unfilled templates for one combination of factors."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    try:
        system = SYSTEM_TEMPLATES[language][row_entity][perspective][wording]
        question = _QUESTION[language][row_entity][perspective][mode][wording]
    except KeyError as exc:
        raise ValueError(
            f"no template for language={language!r}, row_entity={row_entity!r}, "
            f"perspective={perspective!r}, wording={wording!r}"
        ) from exc
    body_key = mode + ("_persona" if perspective == "persona" else "")
    user = _USER_HEAD[language] + _USER_BODY[language][row_entity][body_key] + question
    return PromptTemplate(
        system=system,
        user=user,
        answer_format=answer_format(mode, with_reason, language),
        schema=answer_schema(mode, with_reason),
    )


def fill(template: str, **values: str) -> str:
    """Replace ``{placeholder}`` tokens. Unknown tokens are an error; braces of the JSON answer
    format are left alone because only the known placeholder names are touched."""
    out = template
    for name in PLACEHOLDERS:
        token = "{" + name + "}"
        if token in out:
            if name not in values:
                raise KeyError(f"no value for placeholder {token}")
            out = out.replace(token, values[name])
    return out


def build_prompt(template: PromptTemplate, **values: str) -> tuple[str, str]:
    """Fill both templates and refuse prompts that would leak theory terms."""
    values = {"answer_format": template.answer_format, **values}
    system, user = fill(template.system, **values), fill(template.user, **values)
    leaked = find_banned_terms(system + "\n" + user)
    if leaked:
        raise PromptLeakError(
            f"the prompt mentions {leaked}; prompts must not name the theory or its structures"
        )
    return system, user


__all__ = [
    "BANNED_PATTERNS",
    "MODES",
    "PERSPECTIVES",
    "PLACEHOLDERS",
    "SYSTEM_TEMPLATES",
    "WORDINGS",
    "PromptLeakError",
    "PromptTemplate",
    "answer_format",
    "answer_schema",
    "build_prompt",
    "fill",
    "find_banned_terms",
    "get_template",
]
