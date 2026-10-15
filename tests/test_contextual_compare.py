"""Per-level metrics and the simulation comparison (baselines vs. contextual structures)."""

from __future__ import annotations

import numpy as np
import pytest

from gcm.common import StructureKind
from gcm.contextual import compare as cp
from gcm.contextual import metrics
from gcm.contextual.netlogo_adapter import rule_based_as_export
from gcm.contextual.scenario import load_scenarios
from gcm.contextual.structure_io import StructureExport
from gcm.fortran import FortranComponents, FortranParameters, GarbageCanFortran, Load
from gcm.netlogo import GarbageCanABM, NetLogoParameters, Structure


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios()


# ------------------------------------------------------------------------------- FORTRAN metrics
def test_level_groups():
    assert metrics.level_groups(10, 2).tolist() == [1] * 5 + [2] * 5
    assert metrics.level_groups(10, 3).tolist() == [1, 1, 1, 1, 2, 2, 2, 3, 3, 3]
    with pytest.raises(ValueError):
        metrics.level_groups(10, 11)


def test_fortran_level_metrics_add_up_to_the_summary_statistics():
    from gcm.fortran.statistics import summarise

    params = FortranParameters()
    comps = FortranComponents.classic(
        access=StructureKind.HIERARCHICAL, decision=StructureKind.HIERARCHICAL, params=params
    )
    model = GarbageCanFortran(params, Load.MODERATE, comps)
    history = model.run()
    stats = summarise(
        history, model.energy_reserve, model.energy_wastage, model.state.dm_resting_periods
    )
    m = metrics.fortran_level_metrics(history, n_levels=2)
    assert m["choices_L1"] == 5 and m["problems_L2"] == 10
    assert m["choices_made_L1"] + m["choices_made_L2"] == stats.choices_made
    assert m["by_resolution_L1"] + m["by_resolution_L2"] == stats.by_resolution
    assert m["by_flight_L1"] + m["by_flight_L2"] == stats.by_flight
    assert m["decision_time_L1"] + m["decision_time_L2"] == stats.choice_persistence
    assert m["problem_latency_L1"] + m["problem_latency_L2"] == stats.problem_latency
    assert m["problem_persistence_L1"] + m["problem_persistence_L2"] == stats.problem_persistence
    solved = 20 - stats.problems_not_solved
    assert m["problems_solved_L1"] + m["problems_solved_L2"] == solved
    assert 10 * (m["problems_solved_share_L1"] + m["problems_solved_share_L2"]) == pytest.approx(
        solved
    )
    # in the hierarchical structures important choices resolve less often (paper, property 7)
    assert m["resolution_share_L1"] <= m["resolution_share_L2"]
    assert m["time_to_solution_L2"] >= 1


# ------------------------------------------------------------------------------- NetLogo metrics
def test_observed_model_runs_identically_and_records_blocked_durations():
    p = NetLogoParameters(seed=4, stop_at=400).with_structures(Structure.COMPETENT_HIERARCHY)
    base = GarbageCanABM(p, record_events=True)
    observed = metrics.ObservedGarbageCanABM(p)
    rb, ro = base.run(400).as_dict(), observed.run(400).as_dict()
    assert rb == ro
    assert [e.__dict__ for e in base.events] == [e.__dict__ for e in observed.events]
    frame = observed.event_frame()
    decisions = frame[frame["kind"].isin(["resolution", "oversight"])]
    assert len(decisions) == rb["decisions"]
    assert (decisions.loc[~decisions["after_block"], "blocked_for"] == 0).all()
    after = decisions[decisions["after_block"]]
    assert len(after) == rb["num_blocked_resolutions"] + rb["num_blocked_oversights"]
    assert (after["blocked_for"] >= 1).all()
    assert set(frame["level"].dropna()) <= {1, 2}
    high = decisions[decisions["level"] == 1]
    assert len(high) == rb["num_resolutions_high"] + rb["num_oversights_high"]
    m = metrics.netlogo_level_metrics(observed)
    assert (
        m["resolutions_L1"] == rb["num_resolutions_high"]
        and m["oversights_L2"] == rb["num_oversights_low"]
    )
    assert m["after_block_L1"] + m["after_block_L2"] == len(after)
    pyramid = metrics.netlogo_level_metrics(observed, levels="pyramid")
    assert sum(pyramid[k] for k in pyramid if k.startswith("decisions_L")) == rb["decisions"]
    assert "decisions_L7" in pyramid and "decisions_L8" not in pyramid


def test_levels_are_available_even_without_a_rule_based_hierarchy():
    p = NetLogoParameters(seed=1, stop_at=300).with_structures(Structure.ORGANIZED_ANARCHY)
    model = metrics.ObservedGarbageCanABM(p)
    results = model.run(300)
    assert results.num_resolutions_high is None  # the model itself reports none
    m = metrics.netlogo_level_metrics(model)
    assert m["decisions_L1"] + m["decisions_L2"] == results.decisions
    assert m["decisions_L1"] >= 0 and "postponements_L2" in m


# ------------------------------------------------------------------------------- comparison
def test_fortran_conditions_run_the_same_situations_and_match_the_classic_runs(scenarios):
    s = scenarios["reference_specialized"]
    contextual = cp.FortranCondition(
        "ctx", export=StructureExport.from_matrix(s.expected_matrix, s)
    )
    df = cp.run_fortran_conditions(
        [*cp.fortran_reference_conditions(), contextual], entry_conditions=["choices_a/problems_a"]
    )
    assert df.shape[0] == 4 * 27 and df["situation"].nunique() == 27
    ref = df[df["condition"] == "D_specialized"].drop(columns=["condition", "decision_structure"])
    ctx = df[df["condition"] == "ctx"].drop(columns=["condition", "decision_structure"])
    assert ref.reset_index(drop=True).equals(ctx.reset_index(drop=True))
    table = cp.style_table(df)
    assert table["by_resolution_share"].between(0, 1).all()
    assert table["by_resolution_share"].nunique() == 3  # the reference, not ctx, is distinct
    test = cp.style_chi_square(df, conditions=["D_unsegmented", "D_specialized"])
    assert test.p_value < 1e-6 and 0 < test.cramers_v < 1 and test.dof == 2
    same = cp.style_chi_square(df, conditions=["D_specialized", "ctx"])
    assert same.chi2 == pytest.approx(0.0) and same.p_value == pytest.approx(1.0)


def test_fortran_sampling_mode_draws_per_situation(scenarios):
    s = scenarios["reference_hierarchical"]
    export = StructureExport.from_matrix(s.expected_matrix, s)
    export.probability = np.where(s.expected_matrix, 0.9, 0.1)
    sampled = cp.FortranCondition("sampled", export=export, mode="sample")
    df = cp.run_fortran_conditions(
        [sampled], entry_conditions=["choices_a/problems_a"], loads=[Load.LIGHT]
    )
    assert df["decision_structure"].nunique() == 9  # one draw per situation
    assert df["decision_structure"].iloc[0].endswith("sample@0")


def test_netlogo_conditions_pair_seeds_and_reproduce_the_rule_based_baseline():
    p = NetLogoParameters(stop_at=250).with_structures(Structure.COMPETENT_HIERARCHY)
    probe = GarbageCanABM(replace_seed(p, 0), record_events=False)
    export, assignment = rule_based_as_export(probe, Structure.COMPETENT_HIERARCHY)
    conditions = [
        cp.NetLogoCondition("competent", p),
        cp.NetLogoCondition("ctx competent", p, export=export, assignment=assignment),
        cp.NetLogoCondition("anarchy", p.with_structures(Structure.ORGANIZED_ANARCHY)),
    ]
    df = cp.run_netlogo_conditions(conditions, seeds=[0, 1], ticks=250, workers=2)
    assert df.shape[0] == 6 and sorted(df["seed"].unique()) == [0, 1]
    # the role counts were taken from the seed-0 population, so seed 0 must match exactly
    drop = ["condition", "decision_structure"]
    a = df[(df["condition"] == "competent") & (df["seed"] == 0)].drop(columns=drop)
    b = df[(df["condition"] == "ctx competent") & (df["seed"] == 0)].drop(columns=drop)
    assert a.reset_index(drop=True).equals(b.reset_index(drop=True))
    assert (df["availability_structure"] == "competent hierarchy").sum() == 4
    other = conditions[1].with_other_structures(Structure.ORGANIZED_ANARCHY)
    assert other.params.availability_structure is Structure.ORGANIZED_ANARCHY
    assert other.params.decision_structure is Structure.COMPETENT_HIERARCHY
    comparison = cp.compare_metrics(
        df, ["decisions", "share_resolutions"], "competent", paired_on="seed"
    )
    row = comparison.set_index(["condition", "metric"]).loc[("ctx competent", "decisions")]
    assert abs(row["difference"]) < 10 and row["n"] == 2
    assert np.isnan(
        comparison.set_index(["condition", "metric"]).loc[("competent", "decisions"), "p_value"]
    )
    test = cp.style_chi_square(df, cp.NETLOGO_STYLES)
    assert test.dof == 2 and 0 <= test.cramers_v <= 1


def replace_seed(p: NetLogoParameters, seed: int) -> NetLogoParameters:
    from dataclasses import replace

    return replace(p, seed=seed)


# ------------------------------------------------------------------------------- statistics
def test_bootstrap_interval_and_effect_sizes():
    rng = np.random.default_rng(0)
    x = rng.normal(10, 2, 200)
    low, high = cp.bootstrap_ci(x, seed=1)
    assert low < x.mean() < high and high - low < 1.5
    assert cp.bootstrap_ci([]) == (pytest.approx(float("nan"), nan_ok=True),) * 2 or np.isnan(
        cp.bootstrap_ci([])[0]
    )
    assert cp.bootstrap_ci([3.0]) == (3.0, 3.0)
    assert cp.cohens_d(x, x + 2) == pytest.approx(-1.0, abs=0.15)
    assert np.isnan(cp.cohens_d([1.0], [2.0, 3.0]))
    assert cp.cramers_v(np.array([[50, 0], [0, 50]])) == pytest.approx(1.0)
    assert cp.cramers_v(np.array([[25, 25], [25, 25]])) == pytest.approx(0.0)
    assert cp.cramers_v(np.array([[50, 0, 0], [0, 50, 0]])) == pytest.approx(1.0)  # empty column
    assert np.isnan(cp.cramers_v(np.array([[50, 0], [0, 0]])))
    import pandas as pd

    df = pd.DataFrame(
        {
            "condition": ["a"] * 30 + ["b"] * 30,
            "seed": list(range(30)) * 2,
            "m": list(rng.normal(0, 1, 30)) + list(rng.normal(3, 1, 30)),
        }
    )
    unpaired = cp.compare_metrics(df, ["m"], "a").set_index("condition")
    paired = cp.compare_metrics(df, ["m"], "a", paired_on="seed").set_index("condition")
    for table in (unpaired, paired):
        assert table.loc["b", "p_value"] < 1e-4 and table.loc["b", "cohens_d"] > 2
        assert (
            table.loc["b", "diff_ci_low"]
            < table.loc["b", "difference"]
            < table.loc["b", "diff_ci_high"]
        )
        assert 2 < table.loc["b", "difference"] < 4
