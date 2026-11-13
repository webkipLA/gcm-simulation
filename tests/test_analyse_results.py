"""The analysis script must not mix the runs of the thesis with runs of the newer batch options
(other seeds, university_audit, university_np, other thinking settings). Mock answers only."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from gcm.contextual.connectors import MockConnector
from gcm.contextual.experiment import ExperimentConfig, run_experiment
from gcm.contextual.scenario import load_scenarios

ROOT = Path(__file__).resolve().parents[1]
GEMINI = {"connector": "gemini", "model": "gemini-3.5-flash-lite", "thinking_budget": None, "thinking_level": "minimal"}
MAIN = ExperimentConfig("", mode="per_row", loops=5, temperature=0.7)


@pytest.fixture(scope="module")
def ar():
    spec = importlib.util.spec_from_file_location("analyse_results", ROOT / "scripts" / "analyse_results.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios()


class _As(MockConnector):
    """A Mock whose records carry the identity of another connector, as the run logs of a model do."""

    def __init__(self, *args, identity: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self._identity = identity

    def identity(self) -> dict:
        return self._identity


@pytest.fixture
def logs(tmp_path, monkeypatch, scenarios):
    """Writes run logs like run_batch.py does and returns the function that adds one."""
    monkeypatch.setenv("GCM_DATA_DIR", str(tmp_path))

    def write(scenario_id: str, identity: dict = GEMINI, **changes) -> str:
        s = scenarios[scenario_id]
        cfg = replace(MAIN, scenario_id=scenario_id, **changes)
        connector = _As.for_scenario(s, identity=identity, noise=0.1, seed=cfg.seed)
        return run_experiment(s, cfg, connector, log_dir=tmp_path / "llm_runs").log_path.name

    return write


def test_main_run_is_found_next_to_other_seeds_and_the_new_stages(ar, logs, scenarios):
    main = logs("university_strong_power")
    logs("university_strong_power", seed=1)  # run_batch.py --seed 1
    logs("university_strong_power", loops=2, item_order="shuffled")  # university_audit
    logs("university_strong_power", loops=2, language="de")
    logs("university_strong_power_no_participation")  # university_np
    logs("university_strong_power", identity={**GEMINI, "model": "another-model"})
    runs = ar.load_runs(scenarios)
    assert len(runs) == 6
    hit = ar.pick(runs, ar.GEMINI, "university_strong_power", temperature=0.7, loops=5, mode="per_row")
    assert hit["file"] == main and hit["fac"]["seed"] == 0 and hit["scen"].id == "university_strong_power"
    # another seed is used only when it is asked for
    other = ar.pick(runs, ar.GEMINI, "university_strong_power", temperature=0.7, loops=5, mode="per_row", seed=1)
    assert other["file"] != main and other["fac"]["seed"] == 1


def test_two_thinking_settings_for_one_configuration_stop_the_analysis(ar, logs, scenarios):
    a = logs("reference_hierarchical")
    b = logs("reference_hierarchical", identity={**GEMINI, "thinking_level": "low"})
    with pytest.raises(LookupError) as info:
        ar.pick(ar.load_runs(scenarios), ar.GEMINI, "reference_hierarchical", temperature=0.7, loops=5, mode="per_row")
    message = str(info.value)
    assert a in message and b in message and "level=minimal" in message and "level=low" in message
    with pytest.raises(LookupError, match="0 matching run logs$"):
        ar.pick(ar.load_runs(scenarios), ar.GEMINI, "reference_specialized", temperature=0.7, loops=5, mode="per_row")


def test_configuration_table_tells_seeds_and_thinking_settings_apart(ar, logs, scenarios):
    logs("university_weak_power")
    logs("university_weak_power", seed=2)
    logs("university_weak_power_no_participation")
    logs("university_weak_power", identity={"connector": "ollama", "model": "qwen3:4b", "url": "u", "think": False})
    table = ar.ff2_table(ar.load_runs(scenarios))
    assert list(table.columns[:3]) == ["model", "scenario", "expected"]
    assert list(table.columns[-3:]) == ["file", "seed", "thinking"]  # the new columns come last
    assert len(table) == 4 and table["file"].is_unique
    assert not table.duplicated(subset=["model", "scenario", "seed", "thinking", "loops", "temperature"]).any()
    assert sorted(table["seed"]) == [0, 0, 0, 2]
    assert set(table["thinking"]) == {"level=minimal", "think=false"}
    assert set(table["scenario"]) == {"university_weak_power", "university_weak_power_no_participation"}


def test_tokens_of_openai_compatible_servers_are_counted(ar, logs, scenarios, tmp_path):
    import json

    name = logs("reference_unsegmented", identity={"connector": "university", "model": "m", "base_url": "u",
                                                   "structured": "json_schema"}, loops=1)
    path = tmp_path / "llm_runs" / name
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for r in records:
        r["usage"] = {"prompt_tokens": 700, "completion_tokens": 40, "total_tokens": 740}
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    row = ar.ff2_table(ar.load_runs(scenarios)).iloc[0]
    assert (row["tokens_in"], row["tokens_out"], row["thinking"]) == (700, 40, "")
