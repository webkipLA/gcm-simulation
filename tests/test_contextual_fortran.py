"""The exported structure inside the FORTRAN port."""

from __future__ import annotations

import numpy as np
import pytest

from gcm.common import StructureKind
from gcm.contextual import aggregate as agg
from gcm.contextual.connectors import MockConnector
from gcm.contextual.experiment import ExperimentConfig, run_experiment
from gcm.contextual.fortran_adapter import ContextualAccessStructure, ContextualDecisionStructure
from gcm.contextual.scenario import load_scenarios
from gcm.contextual.structure_io import StructureExport
from gcm.fortran import FortranComponents, FortranParameters, GarbageCanFortran, Load
from gcm.fortran.interfaces import AccessStructure, DecisionStructure


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios()


def _run(components, load=Load.MODERATE, params=None):
    params = params or FortranParameters()
    return GarbageCanFortran(params, load, components).run()


def _same(h1, h2) -> bool:
    return (
        np.array_equal(h1.choices, h2.choices)
        and np.array_equal(h1.decision_makers, h2.decision_makers)
        and np.array_equal(h1.problems, h2.problems)
    )


@pytest.mark.parametrize("kind", [k.value for k in StructureKind])
@pytest.mark.parametrize("load", list(Load))
def test_llm_structure_recovered_from_a_reference_scenario_reproduces_the_classic_run(
    scenarios, kind, load
):
    """End to end: scenario text → mock answers → export → file → component → identical histories."""
    s = scenarios[f"reference_{kind}"]
    result = run_experiment(s, ExperimentConfig(s.id, loops=2), MockConnector.for_scenario(s))
    export = StructureExport.from_estimate(agg.aggregate(result.records, s), s)
    params = FortranParameters()
    for access in StructureKind:
        classic = FortranComponents.classic(
            access=access, decision=StructureKind(kind), params=params
        )
        contextual = FortranComponents.classic(access=access, params=params)
        contextual.decision_structure = ContextualDecisionStructure(export)
        assert isinstance(contextual.decision_structure, DecisionStructure)
        assert _same(_run(classic, load, params), _run(contextual, load, params))


def test_orientation_is_transposed_exactly_once(scenarios):
    s = scenarios["reference_hierarchical"]
    component = ContextualDecisionStructure(StructureExport.from_matrix(s.expected_matrix, s))
    m = component.matrix(None)
    assert m.shape == (10, 10) and m.dtype == bool
    assert m[0].tolist() == [True] + [False] * 9  # choice 1 admits decision maker 1 only
    assert m[9].all()  # choice 10 admits everybody
    assert np.array_equal(component.participants_by_opportunities, s.expected_matrix)
    assert component.name == "contextual:reference_hierarchical:threshold"


def test_wrong_shape_or_entity_is_refused(scenarios):
    s = scenarios["reference_unsegmented"]
    small = StructureExport(
        scenario_id="x",
        row_entity="participant",
        row_ids=("a", "b"),
        col_ids=("x", "y", "z"),
        row_labels=("a", "b"),
        col_labels=("x", "y", "z"),
        probability=np.ones((2, 3)),
        valid_n=np.ones((2, 3), dtype=int),
        binary=np.ones((2, 3), dtype=bool),
    )
    with pytest.raises(ValueError, match="needs 10 participants and 10 opportunities"):
        ContextualDecisionStructure(small)
    with pytest.raises(ValueError, match="needs problems"):
        ContextualAccessStructure(StructureExport.from_matrix(s.expected_matrix, s))


def test_sampling_mode_draws_one_matrix_per_component_with_a_seed(scenarios):
    s = scenarios["reference_hierarchical"]
    result = run_experiment(
        s, ExperimentConfig(s.id, loops=8), MockConnector.for_scenario(s, noise=0.25, seed=4)
    )
    export = StructureExport.from_estimate(agg.aggregate(result.records, s), s)
    a = ContextualDecisionStructure(export, mode="sample", seed=1)
    b = ContextualDecisionStructure(export, mode="sample", seed=1)
    c = ContextualDecisionStructure(export, mode="sample", seed=2)
    assert np.array_equal(a.matrix(None), b.matrix(None))
    assert not np.array_equal(a.matrix(None), c.matrix(None))
    assert a.name == "contextual:reference_hierarchical:sample@1"
    draws = np.array(
        [
            ContextualDecisionStructure(export, mode="sample", seed=k).matrix(None).T
            for k in range(300)
        ]
    )
    assert draws.mean(axis=0) == pytest.approx(export.probability, abs=0.1)
    # the matrix is fixed within a run: the same object answers the same in every period
    model = GarbageCanFortran(FortranParameters(), Load.LIGHT, FortranComponents.classic())
    model.components.decision_structure = a
    first = a.matrix(model.state).copy()
    model.run()
    assert np.array_equal(first, a.matrix(model.state))
    with pytest.raises(ValueError, match="mode"):
        ContextualDecisionStructure(export, mode="random")


def test_degenerate_structures_run_but_are_visible(scenarios):
    s = scenarios["reference_unsegmented"]
    binary = s.expected_matrix.copy()
    binary[:, 2] = False  # nobody may enter opportunity 3
    export = StructureExport.from_matrix(binary, s)
    assert export.degenerate["opportunities_without_row"] == ["c03"]
    comps = FortranComponents.classic()
    comps.decision_structure = ContextualDecisionStructure(export)
    history = _run(comps, Load.LIGHT)
    # Nobody ever works on choice 3, so it never resolves a problem. It is still "made": in the
    # FORTRAN program a choice without attached problems requires zero energy, so an unattended
    # choice is made by oversight (or by flight, if problems visited it and left). This is a
    # property of the model, and the reason degenerate structures are reported, not repaired.
    assert (history.decision_makers == 3).sum() == 0
    assert history.outcomes[2].problems_solved == ()
    assert history.outcomes[2].style is not None and history.outcomes[2].style.value != "resolution"


def test_access_structure_counterpart_takes_a_problem_export(scenarios):
    s = scenarios["reference_unsegmented"]
    from dataclasses import replace

    problems = tuple(replace(e, id=f"p{i:02d}") for i, e in enumerate(s.rows * 2, start=1))
    scenario = replace(s, id="problems_demo", row_entity="problem", rows=problems)
    from gcm.fortran.structures import access_structure

    a1 = access_structure(StructureKind.HIERARCHICAL)._matrix  # [problem, choice]
    export = StructureExport.from_matrix(a1, scenario)
    component = ContextualAccessStructure(export)
    assert isinstance(component, AccessStructure)
    assert np.array_equal(component.matrix(None), a1)
    classic = FortranComponents.classic(access=StructureKind.HIERARCHICAL)
    contextual = FortranComponents.classic()
    contextual.access_structure = component
    assert _same(_run(classic), _run(contextual))
