"""Experiment runner, aggregation and export, with the Mock connector only."""

from __future__ import annotations

import numpy as np
import pytest

from gcm.common import StructureKind
from gcm.contextual import aggregate as agg
from gcm.contextual.cache import DiskCache
from gcm.contextual.connectors import ConnectorError, MockConnector
from gcm.contextual.experiment import (
    ExperimentConfig,
    expand_grid,
    n_calls,
    plan_calls,
    run_experiment,
)
from gcm.contextual.references import reference_matrices
from gcm.contextual.runlog import read_jsonl
from gcm.contextual.scenario import load_scenarios
from gcm.contextual.structure_io import StructureExport


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios()


@pytest.fixture(scope="module")
def hier(scenarios):
    return scenarios["reference_hierarchical"]


class _Counting(MockConnector):
    """A Mock that counts the calls that reach it (and can refuse some of them)."""

    def __init__(self, *args, fail_rows=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = 0
        self.fail_rows = set(fail_rows)

    def _call(self, system, user, temperature, seed, schema, meta):
        self.calls += 1
        if meta["row_id"] in self.fail_rows:
            raise ConnectorError("refused")
        return super()._call(system, user, temperature, seed, schema, meta)


# ------------------------------------------------------------------------------- planning
def test_number_of_calls_is_known_before_running(hier):
    pairwise = ExperimentConfig(hier.id, loops=4)
    per_row = ExperimentConfig(hier.id, loops=4, mode="per_row")
    assert n_calls(hier, pairwise) == 400 == len(plan_calls(hier, pairwise))
    assert n_calls(hier, per_row) == 40 == len(plan_calls(hier, per_row))
    grid = expand_grid(pairwise, representation=["prose", "statute"], language=["en", "de"])
    assert len(grid) == 4 and len({c.config_hash for c in grid}) == 4
    assert grid[1].label() == "prose|a|observer|canonical|de"
    with pytest.raises(ValueError, match="representation"):
        ExperimentConfig(hier.id, representation="table")
    with pytest.raises(ValueError, match="configuration is for"):
        plan_calls(hier, ExperimentConfig("other"))


def test_loops_are_distinct_samples_and_shuffling_is_per_loop(hier):
    canonical = plan_calls(hier, ExperimentConfig(hier.id, loops=3))
    by_loop = [[r for r in canonical if r.loop == k] for k in range(3)]
    assert [r.user for r in by_loop[0]] == [r.user for r in by_loop[1]]
    assert len({r.call_seed for r in canonical}) == len(canonical)
    shuffled = plan_calls(hier, ExperimentConfig(hier.id, loops=3, item_order="shuffled"))
    first = [r.user for r in shuffled if r.loop == 0]
    second = [r.user for r in shuffled if r.loop == 1]
    assert first != second
    assert shuffled == plan_calls(hier, ExperimentConfig(hier.id, loops=3, item_order="shuffled"))
    per_row = plan_calls(
        hier, ExperimentConfig(hier.id, loops=2, mode="per_row", item_order="shuffled")
    )
    assert sorted(per_row[0].col_ids) == list(hier.col_ids) != list(per_row[0].col_ids)
    assert f"- [{per_row[0].col_ids[0]}] " in per_row[0].user


# ------------------------------------------------------------------------------- recovery
@pytest.mark.parametrize("kind", [k.value for k in StructureKind])
@pytest.mark.parametrize(
    "factors",
    [
        {},
        {"representation": "statute", "language": "de", "wording": "b"},
        {"representation": "role_list", "perspective": "persona", "item_order": "shuffled"},
        {"mode": "per_row", "with_reason": False, "show_importance": True},
    ],
)
def test_reference_structures_are_recovered_exactly_without_noise(scenarios, kind, factors):
    """The pipeline end to end: description → queries → answers → matrix → nearest reference."""
    s = scenarios[f"reference_{kind}"]
    config = ExperimentConfig(s.id, loops=2, **factors)
    result = run_experiment(s, config, MockConnector.for_scenario(s))
    assert result.complete and result.n_new == n_calls(s, config) and result.n_errors == 0
    estimate = agg.aggregate(result.records, s)
    assert (estimate.valid == 2).all() and estimate.invalid.sum() == 0
    assert np.array_equal(agg.binarize(estimate.share), s.expected_matrix)
    assert agg.nearest_reference(estimate.share, reference_matrices(10, 10)) == kind


def test_noisy_answers_still_identify_the_structure(hier):
    config = ExperimentConfig(hier.id, loops=15)
    result = run_experiment(hier, config, MockConnector.for_scenario(hier, noise=0.2, seed=3))
    estimate = agg.aggregate(result.records, hier)
    table = agg.distances(estimate.share, reference_matrices(10, 10)).set_index("reference")
    assert table.loc["hierarchical", "hamming"] <= 3
    assert table["hamming"].idxmin() == "hierarchical"
    assert 0.1 < table.loc["hierarchical", "mean_abs_error"] < 0.3  # shares keep the noise


# ------------------------------------------------------------------------------- cache and log
def test_a_second_run_never_repeats_a_call(hier, tmp_path):
    config = ExperimentConfig(hier.id, loops=2)
    cache = DiskCache(tmp_path / "cache")
    mock = _Counting(hier.expected_matrix, hier.row_ids, hier.col_ids, noise=0.1)
    idle = run_experiment(hier, config, mock, cache=cache, cache_only=True)
    assert mock.calls == 0 and idle.n_missing == 200 and not idle.complete and not idle.records
    first = run_experiment(hier, config, mock, cache=cache, log_dir=tmp_path / "runs")
    assert mock.calls == 200 and first.n_new == 200 and first.n_cached == 0
    second = run_experiment(hier, config, mock, cache=cache, log_dir=tmp_path / "runs")
    assert mock.calls == 200 and second.n_new == 0 and second.n_cached == 200

    def strip(records):
        return [{k: v for k, v in r.items() if k != "cached"} for r in records]

    assert strip(first.records) == strip(second.records)
    assert first.log_path == second.log_path and len(read_jsonl(first.log_path)) == 200
    more = run_experiment(hier, ExperimentConfig(hier.id, loops=3), mock, cache=cache)
    assert more.n_cached == 200 and more.n_new == 100  # only the new loop is asked


def test_log_records_carry_everything_needed_to_reproduce_a_call(hier, tmp_path):
    config = ExperimentConfig(hier.id, loops=1, representation="statute", language="de", seed=11)
    result = run_experiment(
        hier, config, MockConnector.for_scenario(hier), log_dir=tmp_path / "runs"
    )
    record = read_jsonl(result.log_path)[0]
    for key in (
        "timestamp", "connector", "model", "model_id", "template_hash", "scenario",
        "representation", "factors", "seed", "call_seed", "temperature", "loop", "row_id",
        "col_ids", "system", "user", "text", "parsed", "cells", "error", "latency_s", "usage",
        "request_key",
    ):  # fmt: skip
        assert key in record, key
    assert record["connector"] == "mock" and record["representation"] == "statute"
    assert record["factors"]["language"] == "de" and record["seed"] == 11
    assert record["template_hash"] == result.template_hash and record["timestamp"].endswith(
        "+00:00"
    )
    assert "§ 1 Organisation" in record["user"]
    assert result.model_ids == ["mock(noise=0)"]


def test_failed_calls_are_counted_and_not_cached(hier, tmp_path):
    config = ExperimentConfig(hier.id, loops=1)
    cache = DiskCache(tmp_path / "cache")
    flaky = _Counting(hier.expected_matrix, hier.row_ids, hier.col_ids, fail_rows={"m04"})
    result = run_experiment(hier, config, flaky, cache=cache)
    assert result.n_errors == 10 and len(cache) == 90
    estimate = agg.aggregate(result.records, hier)
    assert estimate.errors[3].tolist() == [1] * 10 and estimate.valid[3].sum() == 0
    flaky.fail_rows.clear()
    again = run_experiment(hier, config, flaky, cache=cache)
    assert again.n_cached == 90 and again.n_new == 10 and again.n_errors == 0


# ------------------------------------------------------------------------------- aggregation
def test_invalid_answers_are_counted_and_never_defaulted(hier):
    config = ExperimentConfig(hier.id, loops=4)
    result = run_experiment(
        hier, config, MockConnector.for_scenario(hier, invalid_rate=0.5, seed=2)
    )
    estimate = agg.aggregate(result.records, hier)
    assert estimate.invalid.sum() > 100 and (estimate.valid + estimate.invalid == 4).all()
    assert 0.3 < estimate.invalid_share < 0.7
    known = estimate.valid > 0
    assert np.array_equal(estimate.share[known] >= 0.5, hier.expected_matrix[known])
    nothing = run_experiment(hier, config, MockConnector.for_scenario(hier, invalid_rate=1.0))
    empty = agg.aggregate(nothing.records, hier)
    assert empty.valid.sum() == 0 and np.isnan(empty.share).all()
    with pytest.raises(agg.UndeterminedCellsError, match="100 cell"):
        agg.binarize(empty.share)
    with pytest.raises(agg.UndeterminedCellsError):
        StructureExport.from_estimate(empty, hier)
    assert not agg.binarize(empty.share, on_missing="deny").any()  # only when asked for
    assert agg.uncertain_cells(empty).all()


def test_wilson_interval_matches_known_values():
    low, high = agg.wilson_interval(np.array([0, 5, 10, 0]), np.array([10, 10, 10, 0]))
    assert low[:3] == pytest.approx([0.0, 0.2366, 0.7225], abs=1e-4)
    assert high[:3] == pytest.approx([0.2775, 0.7634, 1.0], abs=1e-4)
    assert np.isnan(low[3]) and np.isnan(high[3])


def test_binarization_by_threshold_and_by_sampling():
    share = np.array([[0.0, 0.49, 0.5], [0.51, 1.0, 0.8]])
    assert agg.binarize(share).tolist() == [[False, False, True], [True, True, True]]
    assert agg.binarize(share, 0.8).tolist() == [[False, False, False], [False, True, True]]
    draws = np.array([agg.sample_binary(share, np.random.default_rng(s)) for s in range(400)])
    assert np.array_equal(
        agg.sample_binary(share, np.random.default_rng(7)),
        agg.sample_binary(share, np.random.default_rng(7)),
    )
    assert draws[:, 0, 0].sum() == 0 and draws[:, 1, 1].all()
    assert draws.mean(axis=0) == pytest.approx(share, abs=0.08)


def test_degenerate_structures_are_reported(hier):
    binary = hier.expected_matrix.copy()
    binary[4, :] = False  # a participant without any opportunity
    binary[:, 0] = False  # an opportunity nobody may enter
    report = agg.degeneracy(binary, hier.row_ids, hier.col_ids)
    assert report == {"rows_without_opportunity": ["m05"], "opportunities_without_row": ["c01"]}
    export = StructureExport.from_matrix(binary, hier)
    assert export.degenerate == report and export.to_dict()["degenerate"] == report
    assert np.array_equal(export.binary, binary)  # reported, not repaired


def test_agreement_and_distance_tables(scenarios, hier):
    def estimate(scenario, **kw):
        result = run_experiment(
            scenario,
            ExperimentConfig(scenario.id, loops=3),
            MockConnector.for_scenario(scenario, **kw),
        )
        return agg.aggregate(result.records, scenario)

    estimates = {
        "model A": estimate(hier),
        "model B": estimate(hier),
        "model C": estimate(scenarios["reference_specialized"]),
    }
    table = agg.agreement_table(estimates).set_index(["a", "b"])
    assert table.loc[("model A", "model B"), "agreement"] == 1.0
    assert table.loc[("model A", "model B"), "kappa"] == pytest.approx(1.0)
    assert table.loc[("model A", "model C"), "agreement"] == pytest.approx(0.55)
    assert 0 < table.loc[("model A", "model C"), "kappa"] < 0.5
    assert agg.cohen_kappa(np.ones((2, 2)), np.ones((2, 2))) != agg.cohen_kappa(
        np.ones((2, 2)), np.ones((2, 2))
    )  # NaN: agreement by chance is certain
    dist = agg.distance_table(estimates, reference_matrices(10, 10)).set_index("estimate")
    assert (
        dist.loc["model A", "nearest"] == "hierarchical"
        and dist.loc["model A", "hierarchical"] == 0
    )
    assert dist.loc["model C", "nearest"] == "specialized"
    assert dist.loc["model A", "unsegmented"] == pytest.approx(0.45)


# ------------------------------------------------------------------------------- export
def test_export_keeps_both_matrices_and_survives_a_roundtrip(hier, tmp_path):
    config = ExperimentConfig(hier.id, loops=6)
    result = run_experiment(hier, config, MockConnector.for_scenario(hier, noise=0.15, seed=1))
    estimate = agg.aggregate(result.records, hier, label="demo", meta={"factors": config.as_dict()})
    export = StructureExport.from_estimate(estimate, hier, threshold=0.5)
    path = export.save(tmp_path / "structures" / "demo.json")
    loaded = StructureExport.load(path)
    assert np.array_equal(loaded.binary, export.binary)
    assert loaded.probability == pytest.approx(estimate.share, abs=1e-6)
    assert np.array_equal(loaded.valid_n, estimate.valid)
    assert loaded.row_ids == hier.row_ids and loaded.col_labels == hier.col_labels("en")
    assert loaded.binarization == {"mode": "threshold", "threshold": 0.5, "on_missing": "error"}
    assert loaded.provenance["factors"]["loops"] == 6 and loaded.name == "demo"
    assert 0 < loaded.probability[0, 0] <= 1 and loaded.shape == (10, 10)
    sampled = loaded.sample(np.random.default_rng(0))
    assert sampled.shape == (10, 10) and sampled.dtype == bool
    path.write_text(path.read_text().replace("gcm-contextual-structure/1", "other"))
    with pytest.raises(ValueError, match="not a gcm-contextual-structure"):
        StructureExport.load(path)
