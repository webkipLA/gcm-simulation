"""Scenarios, representations and query templates of the contextual structure pipeline."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from gcm.common import StructureKind
from gcm.contextual import prompts, references
from gcm.contextual.representation import (
    REPRESENTATIONS,
    capitalize,
    entity_sentence,
    item_order,
    render,
)
from gcm.contextual.scenario import ScenarioError, load_scenario_file, load_scenarios
from gcm.fortran.structures import decision_structure


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios()


# ------------------------------------------------------------------------------- references
def test_reference_matrices_are_the_transposed_fortran_structures():
    """The pipeline works with rows = participants; the FORTRAN port stores [choice, dm]."""
    for kind in StructureKind:
        ours = references.reference_matrix(kind, 10, 10)
        assert np.array_equal(ours, decision_structure(kind)._matrix.T)


def test_reference_scenarios_carry_the_matrices_printed_in_the_paper(scenarios):
    for kind in StructureKind:
        s = scenarios[f"reference_{kind.value}"]
        assert s.kind == "reference" and s.shape == (10, 10)
        assert np.array_equal(s.expected_matrix, references.reference_matrix(kind, 10, 10))
        assert np.array_equal(s.target_matrix(), s.expected_matrix)


def test_non_square_references_keep_the_rank_logic():
    hier = references.reference_matrix("hierarchical", 6, 5)
    spec = references.reference_matrix("specialized", 6, 5)
    assert hier[0].all() and hier[-1].tolist() == [False] * 4 + [True]
    assert (spec.sum(axis=1) == 1).all() and spec.any(axis=0).all()
    assert (hier.sum(axis=1)[:-1] >= hier.sum(axis=1)[1:]).all()  # rights shrink with rank


# ------------------------------------------------------------------------------- loading
_MINIMAL = """
id: tiny
title: {en: Tiny, de: Winzig}
organization: {en: An office., de: Ein Büro.}
participants:
  - {id: a, rank: %d, label: {en: the head, de: die Leitung}, description: {en: leads., de: leitet.}}
  - {id: b, label: {en: the clerk, de: die Sachbearbeitung}, description: {en: files, de: ordnet}}
opportunities:
  - {id: x, label: {en: the meeting, de: die Sitzung}, description: {en: meets, de: tagt}}
"""


def test_order_is_the_importance_order_and_ranks_must_agree(tmp_path):
    good = tmp_path / "tiny.yaml"
    good.write_text(_MINIMAL % 1, encoding="utf-8")
    (s,) = load_scenario_file(good)
    assert [e.rank for e in s.rows] == [1, 2] and s.row_ids == ("a", "b")
    assert s.rows[0].description["en"] == "leads"  # the final period is dropped
    assert s.target_matrix() is None and s.kind == "custom"
    bad = tmp_path / "bad.yaml"
    bad.write_text(_MINIMAL % 2, encoding="utf-8")
    with pytest.raises(ScenarioError, match="rank 2 contradicts position 1"):
        load_scenario_file(bad)


def test_missing_language_is_reported(tmp_path):
    path = tmp_path / "tiny.yaml"
    path.write_text((_MINIMAL % 1).replace("de: Winzig", "de: ''"), encoding="utf-8")
    with pytest.raises(ScenarioError, match="title"):
        load_scenario_file(path)


# ------------------------------------------------------------------------------- rendering
def test_every_representation_carries_the_same_content(scenarios):
    for s, variant, language in itertools.product(
        scenarios.values(), REPRESENTATIONS, ("en", "de")
    ):
        text = render(s, variant, language)
        assert s.organization[language] in text
        for statement in s.statements:
            assert statement[language] in text
        for e in (*s.rows, *s.opportunities):
            assert capitalize(e.label[language]) in text
            assert e.description[language] in text


def test_importance_is_hidden_by_default_and_shown_on_request(scenarios):
    s = scenarios["reference_hierarchical"]
    for variant in REPRESENTATIONS:
        assert "rank" not in render(s, variant, "en")
        shown = render(s, variant, "en", show_importance=True)
        assert "Level in the organization: rank 3 of 10" in shown
        assert "Importance: rank 10 of 10" in shown
        assert "Wichtigkeit: Rang 2 von 10" in render(s, variant, "de", show_importance=True)


def test_shuffled_order_is_seeded_and_changes_only_the_order(scenarios):
    s = scenarios["reference_unsegmented"]
    a, b = item_order(s, "shuffled", 1), item_order(s, "shuffled", 1)
    assert a == b and a != item_order(s, "shuffled", 2)
    assert sorted(a.rows) == list(range(10)) and a.rows != tuple(range(10))
    canonical = render(s, "role_list", "en").splitlines()
    shuffled = render(s, "role_list", "en", order=a).splitlines()
    assert canonical != shuffled and sorted(canonical) == sorted(shuffled)


def test_validation_fields_are_never_rendered(scenarios):
    for s in scenarios.values():
        for variant in REPRESENTATIONS:
            text = render(s, variant, "en", show_importance=True)
            assert s.title["en"] not in text
            assert "1111" not in text and "expected" not in text.lower()


# ------------------------------------------------------------------------------- prompts
def test_no_prompt_mentions_the_theory_or_a_structure_name(scenarios):
    """Shipped scenario texts and all templates are free of theory terms."""
    for s, variant, language in itertools.product(
        scenarios.values(), REPRESENTATIONS, ("en", "de")
    ):
        text = render(s, variant, language, show_importance=True)
        assert prompts.find_banned_terms(text) == [], (s.id, variant, language)
    for language, by_entity in prompts.SYSTEM_TEMPLATES.items():
        for entity, by_perspective in by_entity.items():
            for perspective, by_wording in by_perspective.items():
                for wording, mode in itertools.product(by_wording, prompts.MODES):
                    t = prompts.get_template(
                        language=language,
                        row_entity=entity,
                        perspective=perspective,
                        wording=wording,
                        mode=mode,
                    )
                    assert prompts.find_banned_terms(t.system + t.user) == []


def test_banned_terms_are_detected_and_block_the_prompt():
    assert prompts.find_banned_terms("a Garbage-Can process") == ["garbage-can"]
    assert prompts.find_banned_terms("eine organisierte Anarchie") == ["anarch"]
    assert prompts.find_banned_terms("the Hierarchical and the specialised type") == [
        "hierarch",
        "specialised",
    ]
    assert prompts.find_banned_terms("the dean heads a faculty") == []
    t = prompts.get_template()
    with pytest.raises(prompts.PromptLeakError, match="unsegment"):
        prompts.build_prompt(
            t, organization_description="An unsegmented firm.", participant="a", opportunity="b"
        )


def test_templates_fill_all_placeholders_and_keep_the_json_braces(scenarios):
    s = scenarios["reference_hierarchical"]
    t = prompts.get_template(language="en", perspective="persona", wording="b")
    system, user = prompts.build_prompt(
        t,
        organization_description=render(s, "prose", "en"),
        participant=s.rows[2].label["en"],
        participant_description=entity_sentence(s.rows[2], "en"),
        opportunity=s.opportunities[6].label["en"],
    )
    assert "you are the member of grade 3" in system
    assert "The member of grade 3 holds seniority grade 3." in system
    assert '{"reason": "<one short sentence>", "eligible": true or false}' in system
    assert "Decision occasion: the committee of grade 7" in user
    assert "Person:" not in user  # the persona is named in the system message
    for name in prompts.PLACEHOLDERS:
        assert "{" + name + "}" not in system + user
    with pytest.raises(KeyError, match="opportunity"):
        prompts.build_prompt(prompts.get_template(), organization_description="x", participant="a")


def test_answer_format_and_schema_follow_the_switches():
    assert prompts.answer_format("pairwise", False, "en") == '{"eligible": true or false}'
    assert "reason" not in prompts.answer_schema("pairwise", False)["properties"]
    schema = prompts.answer_schema("pairwise", True)
    assert list(schema["properties"]) == ["reason", "eligible"]  # reason before verdict
    per_row = prompts.answer_schema("per_row", True)
    assert per_row["properties"]["answers"]["items"]["required"] == [
        "opportunity",
        "reason",
        "eligible",
    ]
    assert '"answers"' in prompts.answer_format("per_row", True, "de")


def test_template_hash_identifies_the_query_syntax():
    base = prompts.get_template()
    assert base.template_hash == prompts.get_template().template_hash
    others = [
        prompts.get_template(wording="b"),
        prompts.get_template(perspective="persona"),
        prompts.get_template(language="de"),
        prompts.get_template(mode="per_row"),
        prompts.get_template(with_reason=False),
    ]
    hashes = {base.template_hash, *(t.template_hash for t in others)}
    assert len(hashes) == 6
    with pytest.raises(ValueError, match="no template"):
        prompts.get_template(row_entity="problem", perspective="persona")
