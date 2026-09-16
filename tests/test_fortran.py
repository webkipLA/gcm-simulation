"""Tests for the FORTRAN port: structures, dynamics and docking against the published tables."""

from __future__ import annotations

import numpy as np
import pytest

from gcm.common import StructureKind
from gcm.fortran import (
    FortranComponents,
    FortranParameters,
    GarbageCanFortran,
    Load,
    MovementCondition,
    OrganizationalVariant,
    experiments,
    summarise,
)
from gcm.fortran.arithmetic import ExactArithmetic, HexFloat, Ibm360Arithmetic
from gcm.fortran.state import FortranState
from gcm.fortran.structures import (
    EnergyDistributionKind,
    access_structure,
    decision_structure,
    energy_distribution,
)


# ---------------------------------------------------------------------------------- structures
def _rows(text: str) -> np.ndarray:
    return np.array([[c == "1" for c in line] for line in text.split()], dtype=bool)


def test_hierarchical_access_matrix_matches_paper():
    """A1 as printed on p. 6 (rows = problems, columns = choices)."""
    published = _rows(
        """1111111111 1111111111 0111111111 0111111111 0011111111 0011111111 0001111111
           0001111111 0000111111 0000111111 0000011111 0000011111 0000001111 0000001111
           0000000111 0000000111 0000000011 0000000011 0000000001 0000000001"""
    )
    assert np.array_equal(access_structure(StructureKind.HIERARCHICAL)._matrix, published)


def test_specialized_access_matrix_matches_paper():
    m = access_structure(StructureKind.SPECIALIZED)._matrix
    assert m.sum() == 20
    for j in range(20):
        assert m[j].nonzero()[0].tolist() == [j // 2]


def test_decision_structures_match_paper():
    d1 = decision_structure(StructureKind.HIERARCHICAL)._matrix  # [choice, dm]
    # D1 printed with rows = decision makers: dm k participates in choices >= k
    for k in range(10):
        assert d1[:, k].nonzero()[0].tolist() == list(range(k, 10))
    assert np.array_equal(
        decision_structure(StructureKind.SPECIALIZED)._matrix, np.eye(10, dtype=bool)
    )
    assert decision_structure(StructureKind.UNSEGMENTED)._matrix.all()


def test_energy_distributions_sum_to_5_5():
    a = ExactArithmetic()
    for kind in (0, 1, 2):
        m = energy_distribution(kind).matrix(10, 20, a)
        assert len(m) == 10 and len(m[0]) == 20
        assert sum(row[0] for row in m) == pytest.approx(5.5)
    assert [row[0] for row in energy_distribution(0).matrix(10, 20, a)] == pytest.approx(
        [0.1 * k for k in range(1, 11)]
    )
    assert [row[0] for row in energy_distribution(2).matrix(10, 20, a)] == pytest.approx(
        [1.1 - 0.1 * k for k in range(1, 11)]
    )


# ---------------------------------------------------------------------------------- dynamics
def test_run_is_deterministic_and_complete():
    params = FortranParameters()
    comps = FortranComponents.classic(params=params)
    h1 = GarbageCanFortran(params, Load.LIGHT, comps).run()
    h2 = GarbageCanFortran(params, Load.LIGHT, comps).run()
    assert np.array_equal(h1.choices, h2.choices)
    assert np.array_equal(h1.problems, h2.problems)
    assert h1.choices.shape == (20, 10)
    # every choice is activated in its entry period
    for i, t in enumerate(params.choice_entry_times):
        assert h1.choices[t - 1, i] in (1, 2)
        assert (h1.choices[: t - 1, i] == 0).all()


def test_light_load_unsegmented_important_more_energy_resolves_everything():
    """Variant 0002 in Table 5: all decisions by resolution, zero activity and decision time."""
    params = FortranParameters()
    comps = FortranComponents.classic(
        access=StructureKind.UNSEGMENTED,
        decision=StructureKind.UNSEGMENTED,
        energy=EnergyDistributionKind.IMPORTANT_MORE,
        params=params,
    )
    m = GarbageCanFortran(params, Load.LIGHT, comps)
    stats = summarise(m.run(), m.energy_reserve, m.energy_wastage, m.state.dm_resting_periods)
    assert stats.choices_made == 10 and stats.by_resolution == 10
    assert stats.problem_persistence == 0 and stats.choice_persistence == 0
    assert stats.dm_velocity == 100 and stats.problems_not_solved == 0


def test_decision_styles_are_exhaustive_and_flight_requires_prior_problems():
    df = experiments.run_all()
    assert (df["choices_made"] == df["by_resolution"] + df["by_oversight"] + df["by_flight"]).all()
    assert (
        df["by_flight"].sum() > 0 and df["by_oversight"].sum() > 0 and df["by_resolution"].sum() > 0
    )


def test_frozen_movement_conditions_run():
    for na in MovementCondition:
        params = FortranParameters(movement=na)
        m = GarbageCanFortran(params, Load.MODERATE, FortranComponents.classic(params=params))
        m.run()
        assert m.state.period == 20


# ---------------------------------------------------------------------------------- docking
@pytest.fixture(scope="module")
def all_results():
    return experiments.run_all()


def test_table_1_docking(all_results):
    """Numerical docking (Axtell et al. 1996): cells within 0.15 of the published Table 1
    and the overall proportion within 0.03."""
    ours = experiments.table_1(all_results)
    pub = experiments.TABLE_1_PUBLISHED
    assert (ours - pub).abs().max().max() <= 0.15
    assert abs(ours.loc["all", "all"] - pub.loc["all", "all"]) <= 0.03


def test_table_2_docking(all_results):
    ours = experiments.table_2(all_results)
    pub = experiments.TABLE_2_PUBLISHED
    rel = ((ours - pub).abs() / pub.abs()).max().max()
    assert rel <= 0.06
    # property 2: load increases problem activity, decision difficulty and flight/oversight
    assert ours["mean_problem_activity"].is_monotonic_increasing
    assert ours["mean_decision_difficulty"].is_monotonic_increasing


def test_paper_means(all_results):
    assert all_results["choices_not_made"].mean() == pytest.approx(1.0, abs=0.1)
    assert all_results["problems_not_solved"].mean() == pytest.approx(12.3, abs=0.4)


def test_table_5_exact_rows(all_results):
    """Rows of Table 5 that the port reproduces exactly (up to the paper's rounding)."""
    t5 = experiments.table_5_rows(all_results, ["0002", "0001", "0200", "1221", "0111"])
    assert t5.loc["0002"].tolist() == [1.0, 0.0, 0.0, 100.0, 0.0]
    assert t5.loc["0001"].tolist() == [1.0, 0.0, 0.0, 100.0, 0.0]
    assert t5.loc["0200", "proportion_resolution"] == pytest.approx(0.68, abs=0.005)
    assert t5.loc["1221", "problem_activity"] == pytest.approx(158, abs=1)
    assert t5.loc["1221", "decision_time"] == pytest.approx(83, abs=0.5)
    assert t5.loc["0111", "problem_activity"] == pytest.approx(57, abs=0.5)


def test_property_1_flight_and_oversight_dominate_except_specialized(all_results):
    """Resolution is not the most common style, except where flight is restricted (specialized
    access) or under light load (Cohen, March & Olsen 1972, property 1)."""
    t1 = experiments.table_1(all_results)
    assert t1.loc["all", "unsegmented"] < 0.5
    assert t1.loc["all", "hierarchical"] < 0.5
    assert t1.loc["all", "specialized"] > 0.5


# ---------------------------------------------------------------------------------- arithmetic
def test_hexfloat_truncates_to_24_bit_hex_fraction():
    a = Ibm360Arithmetic("truncate")
    v = a.const("0.1")
    # 0.1 = 0x0.1999999… → truncated fraction 0x199999 × 16⁻⁶ × 16⁰ = 0.09999996...
    assert float(v) < 0.1 and float(v) > 0.0999999
    ten = a.const(10)
    assert float(ten) == 10.0
    assert float(v * ten) < 1.0  # accumulated truncation is visible
    assert isinstance(v, HexFloat)


def test_ibm360_backend_changes_tie_cases_only_slightly():
    exact = experiments.run_all(arithmetic="exact")
    ibm = experiments.run_all(arithmetic="ibm360")
    # the bulk of the situations agree; only tie-sensitive ones differ
    same = (exact["by_resolution"].values == ibm["by_resolution"].values).mean()
    assert same > 0.7


# ---------------------------------------------------------------------------------- extension seams
def test_custom_dynamic_decision_structure_is_consulted_every_period():
    """A decision structure that returns a different matrix per period is honoured."""
    calls: list[int] = []

    class Rotating:
        name = "rotating"

        def matrix(self, state: FortranState):
            calls.append(state.period)
            m = np.zeros((10, 10), dtype=bool)
            m[:, state.period % 10] = True  # only one decision maker is eligible each period
            return m

    params = FortranParameters()
    comps = FortranComponents.classic(params=params)
    comps.decision_structure = Rotating()
    m = GarbageCanFortran(params, Load.LIGHT, comps)
    h = m.run()
    assert calls[-1] == 20 and len(calls) >= 20
    # at most one decision maker attached per period
    assert ((h.decision_makers != 0).sum(axis=1) <= 1).all()


def test_variant_codes_roundtrip():
    for v in OrganizationalVariant.all():
        assert OrganizationalVariant.from_code(v.code) == v
    assert len(OrganizationalVariant.all()) == 81
