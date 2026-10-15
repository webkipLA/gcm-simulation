"""The exported structure inside the NetLogo port."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from gcm.contextual.netlogo_adapter import (
    ContextualNetLogoDecisionStructure,
    RoleAssignment,
    rule_based_as_export,
    split_counts,
)
from gcm.contextual.references import reference_matrix
from gcm.contextual.structure_io import StructureExport
from gcm.netlogo import GarbageCanABM, NetLogoComponents, NetLogoParameters, Structure
from gcm.netlogo.agents import Opportunity, Participant, PatchAgents
from gcm.netlogo.interfaces import DecisionStructure


def _export(binary, name="t"):
    binary = np.asarray(binary, dtype=bool)
    r, c = binary.shape
    return StructureExport(
        scenario_id=name,
        row_entity="participant",
        row_ids=tuple(f"r{i}" for i in range(r)),
        col_ids=tuple(f"t{j}" for j in range(c)),
        row_labels=tuple(f"role {i}" for i in range(r)),
        col_labels=tuple(f"type {j}" for j in range(c)),
        probability=binary.astype(float),
        valid_n=np.zeros((r, c), dtype=int),
        binary=binary,
        name=name,
    )


def _results(params, component=None, ticks=600):
    comps = NetLogoComponents.classic(params)
    if component is not None:
        comps.decision_structure = component
    model = GarbageCanABM(params, components=comps, record_events=False)
    return model.run(ticks).as_dict()


# ------------------------------------------------------------------------------- assignment
def test_split_counts_handles_equal_counts_and_shares():
    assert split_counts(100, 3) == (34, 33, 33)
    assert split_counts(100, 4, (10, 20, 30, 40)) == (10, 20, 30, 40)
    assert split_counts(100, 3, (0.5, 0.25, 0.25)) == (50, 25, 25)
    assert split_counts(10, 3, (1, 1, 1)) == (4, 3, 3)  # treated as shares, remainder first
    assert sum(split_counts(7, 3, (0.2, 0.3, 0.5))) == 7
    with pytest.raises(ValueError):
        split_counts(10, 2, (1, 2, 3))


def test_roles_follow_the_ability_mapping_and_types_follow_who():
    p = NetLogoParameters(seed=5, number_of_participants=30, number_of_opportunities=20)
    model = GarbageCanABM(p, record_events=False)
    ids = (("a", "b", "c"), ("x", "y"))
    ranked = RoleAssignment(*ids, ability_mapping="ranked").participant_roles(model.participants)
    by_role = {r: [a.ability for a in model.participants if ranked[a.who] == r] for r in range(3)}
    assert len(by_role[0]) == 10 and min(by_role[0]) >= max(by_role[1]) >= max(by_role[2])
    inverse = RoleAssignment(*ids, ability_mapping="inverse").participant_roles(model.participants)
    assert {w for w, r in ranked.items() if r == 0} == {w for w, r in inverse.items() if r == 2}
    rnd1 = RoleAssignment(*ids, seed=1).participant_roles(model.participants)
    rnd2 = RoleAssignment(*ids, seed=1).participant_roles(model.participants)
    assert rnd1 == rnd2 and rnd1 != RoleAssignment(*ids, seed=2).participant_roles(
        model.participants
    )
    types = RoleAssignment(*ids, opportunities_per_type=(5, 15)).opportunity_types(
        model.opportunities
    )
    assert [types[w] for w in range(20)] == [0] * 5 + [1] * 15  # most important type first
    with pytest.raises(ValueError, match="ability_mapping"):
        RoleAssignment(*ids, ability_mapping="sorted")


# ------------------------------------------------------------------------------- permissions
def test_permissions_are_looked_up_in_the_role_by_type_matrix():
    p = NetLogoParameters(seed=1, number_of_participants=4, number_of_opportunities=4)
    model = GarbageCanABM(p, record_events=False)
    component = ContextualNetLogoDecisionStructure(
        _export([[True, False], [False, True]]),
        RoleAssignment(("r0", "r1"), ("t0", "t1"), ability_mapping="ranked"),
    )
    assert isinstance(component, DecisionStructure)
    able = max(model.participants, key=lambda a: a.ability)
    weak = min(model.participants, key=lambda a: a.ability)
    important, unimportant = model.opportunities[0], model.opportunities[3]
    assert component.participant_may_enter(able, PatchAgents(opportunities=[important]), model)
    assert not component.participant_may_enter(
        able, PatchAgents(opportunities=[unimportant]), model
    )
    assert not component.participant_may_enter(weak, PatchAgents(opportunities=[important]), model)
    assert component.participant_may_enter(weak, PatchAgents(), model)
    assert component.opportunity_may_enter(important, PatchAgents(participants=[able]), model)
    assert not component.opportunity_may_enter(
        important, PatchAgents(participants=[able, weak]), model
    )
    assert component.opportunity_may_enter(unimportant, PatchAgents(), model)
    table = component.assignment_table(model)
    assert table["participants"].tolist() == [2, 2] and table["permitted_types"].tolist() == [
        [0],
        [1],
    ]
    assert component.type_table(model)["opportunities"].tolist() == [2, 2]


def test_all_ones_matrix_reproduces_the_unrestricted_baseline_exactly():
    """The component never touches the model's random stream."""
    p = NetLogoParameters(seed=3, stop_at=600).with_structures(Structure.ORGANIZED_ANARCHY)
    component = ContextualNetLogoDecisionStructure(_export(np.ones((3, 4))))
    assert _results(p) == _results(p, component)
    # the other two structures may stay rule-based next to the contextual decision structure
    p2 = replace(p, decision_structure=Structure.ORGANIZED_ANARCHY)
    p2 = replace(p2, availability_structure=Structure.COMPETENT_HIERARCHY)
    assert _results(p2) == _results(p2, component)


@pytest.mark.parametrize(
    "structure", [Structure.COMPETENT_HIERARCHY, Structure.INCOMPETENT_HIERARCHY]
)
def test_two_by_two_matrix_reproduces_the_rule_based_hierarchies_exactly(structure):
    """Roles split at the ability threshold, types at the hierarchy divide: identical runs."""
    p = NetLogoParameters(seed=8, stop_at=800).with_structures(structure)
    probe = GarbageCanABM(p, record_events=False)
    export, assignment = rule_based_as_export(probe, structure)
    component = ContextualNetLogoDecisionStructure(export, assignment)
    assert component.name.startswith(f"contextual:rule_based_{structure.name.lower()}:ranked")
    assert _results(p) == _results(p, component)
    # and it differs from the other rule-based hierarchy under the same seed
    other = (
        Structure.INCOMPETENT_HIERARCHY
        if structure is Structure.COMPETENT_HIERARCHY
        else Structure.COMPETENT_HIERARCHY
    )
    assert _results(replace(p, decision_structure=other)) != _results(p, component)


def test_reference_structures_expand_to_agents_and_change_the_dynamics():
    p = NetLogoParameters(seed=2, stop_at=500).with_structures(Structure.ORGANIZED_ANARCHY)
    outcomes = {}
    for kind in ("unsegmented", "hierarchical", "specialized"):
        export = _export(reference_matrix(kind, 5, 5), name=kind)
        component = ContextualNetLogoDecisionStructure(
            export, RoleAssignment.for_export(export, ability_mapping="ranked")
        )
        outcomes[kind] = _results(p, component)
    assert outcomes["unsegmented"] == _results(p)
    assert outcomes["hierarchical"]["decisions"] < outcomes["unsegmented"]["decisions"]
    assert outcomes["specialized"]["decisions"] < outcomes["hierarchical"]["decisions"]


def test_sampling_draws_one_matrix_per_run():
    probs = np.array([[1.0, 0.5], [0.5, 0.0]])
    export = _export(np.ones((2, 2)))
    export.probability = probs
    draws = {
        tuple(ContextualNetLogoDecisionStructure(export, mode="sample", seed=s).permitted.ravel())
        for s in range(40)
    }
    assert len(draws) > 1 and all(d[0] and not d[3] for d in draws)
    a = ContextualNetLogoDecisionStructure(export, mode="sample", seed=7).permitted
    b = ContextualNetLogoDecisionStructure(export, mode="sample", seed=7).permitted
    assert np.array_equal(a, b)
    with pytest.raises(ValueError, match="does not match"):
        ContextualNetLogoDecisionStructure(export, RoleAssignment(("x",), ("y",)))


def test_component_rebinds_to_a_new_model():
    export = _export(np.ones((2, 2)))
    component = ContextualNetLogoDecisionStructure(export)
    m1 = GarbageCanABM(NetLogoParameters(seed=1, number_of_participants=6), record_events=False)
    m2 = GarbageCanABM(NetLogoParameters(seed=1, number_of_participants=8), record_events=False)
    component.participant_may_enter(m1.participants[0], PatchAgents(), m1)
    component.bind(m1)
    assert len(component._role) == 6
    component.participant_may_enter(
        m2.participants[7], PatchAgents(opportunities=[m2.opportunities[0]]), m2
    )
    assert len(component._role) == 8
    dummy_o, dummy_p = Opportunity(0, 0, 0), Participant(1, 0, 0)
    assert component.participant_may_enter(dummy_p, PatchAgents(), m2)
    assert component.opportunity_may_enter(dummy_o, PatchAgents(), m2)
