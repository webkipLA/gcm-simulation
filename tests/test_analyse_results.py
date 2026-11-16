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

    def write(scenario_id: str, identity: dict = GEMINI, noise: float = 0.1, **changes) -> str:
        s = scenarios[scenario_id]
        cfg = replace(MAIN, scenario_id=scenario_id, **changes)
        connector = _As.for_scenario(s, identity=identity, noise=noise, seed=cfg.seed)
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
    """For a model without a declared main setting the script cannot choose and says so."""
    other = {"connector": "gemini", "model": "another-model", "thinking_budget": None, "thinking_level": "low"}
    a = logs("reference_hierarchical", identity=other)
    b = logs("reference_hierarchical", identity={**other, "thinking_level": "high"})
    with pytest.raises(LookupError) as info:
        ar.pick(ar.load_runs(scenarios), "another-model", "reference_hierarchical", temperature=0.7, loops=5, mode="per_row")
    message = str(info.value)
    assert a in message and b in message and "level=low" in message and "level=high" in message
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


def test_main_model_with_two_thinking_settings_uses_the_one_of_the_thesis(ar, logs, scenarios):
    main = logs("university_strong_power")  # level=minimal
    low = logs("university_strong_power", identity={**GEMINI, "thinking_level": "low"})
    runs = ar.load_runs(scenarios)
    hit = ar.pick(runs, ar.GEMINI, "university_strong_power", temperature=0.7, loops=5, mode="per_row")
    assert hit["file"] == main != low
    table = ar.ff2_table(runs)
    assert sorted(table["thinking"]) == ["level=low", "level=minimal"]  # both stay in the table


# --------------------------------------------------------- further university conditions
LOW = {**GEMINI, "thinking_level": "low"}
ARGON = {**GEMINI, "model": "gemini-4-argon", "thinking_level": "low"}
QWEN = {"connector": "ollama", "model": "qwen3:4b", "url": "u", "think": False}


def test_pick_takes_an_explicit_thinking_setting_and_optional_runs_may_be_missing(ar, logs, scenarios):
    main = logs("university_strong_power")
    low = logs("university_strong_power", identity=LOW)
    runs = ar.load_runs(scenarios)
    common = dict(temperature=0.7, loops=5, mode="per_row")
    assert ar.pick(runs, ar.GEMINI, "university_strong_power", **common)["file"] == main
    assert ar.pick(runs, ar.GEMINI, "university_strong_power", "level=low", **common)["file"] == low
    assert ar.pick_optional(runs, ar.ARGON, "university_strong_power", "level=low", **common) is None
    assert ar.pick_optional(runs, ar.GEMINI, "university_strong_power_no_participation", **common) is None


def university_logs(logs, extra: bool):
    for key in ("strong", "moderate", "weak"):
        logs(f"university_{key}_power")
        if extra:
            logs(f"university_{key}_power_no_participation", noise=0.45)  # far from the expected form
            logs(f"university_{key}_power", identity=LOW, noise=0.0)  # exactly the expected form
    if extra:
        logs("university_strong_power", identity=ARGON, noise=0.3)


def test_further_university_conditions_are_found_run_and_compared(ar, logs, scenarios):
    university_logs(logs, extra=True)
    runs = ar.load_runs(scenarios)
    common = dict(temperature=0.7, loops=5, mode="per_row")
    uni = {k: ar.export_of(ar.pick(runs, ar.GEMINI, f"university_{k}_power", **common), f"Hochschule {k}")
           for k in ("strong", "moderate", "weak")}
    extra = ar.extra_university_exports(runs)
    assert set(extra) == {("np", "strong"), ("np", "moderate"), ("np", "weak"), ("low", "strong"), ("low", "moderate"),
                          ("low", "weak"), ("argon", "strong")}
    assert extra["np", "strong"].scenario_id == "university_strong_power_no_participation"
    assert extra["np", "weak"].name == "ohne Teilnahmeaussage schwach"

    from gcm.contextual import compare as cp

    un = cp.run_fortran_conditions(cp.fortran_reference_conditions() + [
        cp.FortranCondition(f"Hochschule {g} (Schwelle)", export=uni[k])
        for k, g in (("strong", "stark"), ("moderate", "mittel"), ("weak", "schwach"))])
    both, tests, notes = ar.extra_university(extra, uni, un)
    names = [e.name for e in extra.values()]
    assert set(both.condition) == {"D_unsegmented", "D_hierarchical", "D_specialized", "Hochschule stark (Schwelle)",
                                   "Hochschule mittel (Schwelle)", "Hochschule schwach (Schwelle)", *names}
    assert (both.groupby("condition").size() == 108).all()
    # a condition is compared with the expected form and with the main-model structure, once per distinct matrix
    pairs = set(zip(tests.condition, tests.reference, strict=True))
    assert ("ohne Teilnahmeaussage stark", "D_hierarchical") in pairs
    assert ("ohne Teilnahmeaussage schwach", "D_unsegmented") in pairs
    assert all(c != r for c, r in pairs) and len(tests) == 8 * len(pairs)
    for name, expected in (("Hauptmodell, Denkstufe low stark", "D_hierarchical"),
                           ("Hauptmodell, Denkstufe low schwach", "D_unsegmented")):
        assert f"{name}: Struktur identisch mit {expected}, kein Test" in notes  # noise 0 = the expected form
        assert (name, expected) not in pairs
    assert len(notes) == len(set(notes))
    assert tests.p_holm.between(0, 1).all()


@pytest.mark.parametrize("extra", [False, True])
def test_whole_analysis_runs_with_and_without_the_further_conditions(ar, logs, tmp_path, monkeypatch, capsys, extra):
    logs("reference_hierarchical")
    logs("reference_hierarchical", identity=QWEN, noise=0.3)
    logs("reference_hierarchical", identity=QWEN, noise=0.2, temperature=0.0, loops=2)
    university_logs(logs, extra)
    monkeypatch.setattr("sys.argv", ["analyse_results.py", "--null", "0"])
    ar.main()
    out = tmp_path / "analysis"
    report = (out / "report.md").read_text(encoding="utf-8")
    figures = sorted(p.stem for p in (out / "figures").glob("*.png"))
    old = ["abb_4_2_qwen_hierarchie", "abb_4_3_entscheidungsstile", "abb_4_4_hochschulstrukturen"]
    heading = "## FF3: Hochschulszenario, weitere Bedingungen im FORTRAN-Port"
    assert "## FF3: Hochschulszenario im FORTRAN-Port" in report
    if extra:
        assert heading in report and "ohne Teilnahmeaussage stark" in report and "gemini-4-argon stark" in report
        # the models figure needs all three variants of a model; argon has only one here
        assert figures == [*old, "abb_4_6_hochschule_ohne_teilnahme", "abb_4_7_hochschule_modelle",
                           "abb_4_8_hochschule_entscheidungsstile"]
        assert (out / "ff3_university_extra_summary.csv").exists() and (out / "ff3_university_extra_tests.csv").exists()
    else:
        assert heading not in report and figures == old
        assert not list(out.glob("ff3_university_extra_*"))
    for name in ("ff3_university_runs.csv", "ff3_university_summary.csv", "ff3_reference_summary.csv", "ff2_configs.csv"):
        assert (out / name).exists()


def test_second_arithmetic_goes_to_its_own_folder_and_is_compared_with_the_main_analysis(ar, logs, tmp_path, monkeypatch, capsys):
    logs("reference_hierarchical")
    logs("reference_hierarchical", identity=QWEN, noise=0.3)
    logs("reference_hierarchical", identity=QWEN, noise=0.2, temperature=0.0, loops=2)
    university_logs(logs, extra=True)

    monkeypatch.setattr("sys.argv", ["analyse_results.py", "--null", "0", "--arithmetic", "ibm360"])
    ar.main()  # without a main analysis there is nothing to compare with
    other = tmp_path / "analysis__ibm360"
    assert (other / "report.md").exists() and not (other / "arithmetic_comparison.md").exists()
    assert "run the analysis without --arithmetic first" in capsys.readouterr().out
    assert not (tmp_path / "analysis").exists()

    monkeypatch.setattr("sys.argv", ["analyse_results.py", "--null", "0"])
    ar.main()
    main_report = (tmp_path / "analysis" / "report.md").read_bytes()
    monkeypatch.setattr("sys.argv", ["analyse_results.py", "--null", "0", "--arithmetic", "ibm360"])
    ar.main()
    assert (tmp_path / "analysis" / "report.md").read_bytes() == main_report  # the main analysis is left alone
    assert "Arithmetik ibm360" in (other / "report.md").read_text(encoding="utf-8").splitlines()[0]
    text = (other / "arithmetic_comparison.md").read_text(encoding="utf-8")
    for heading in ("## Referenzszenarien", "## Hochschulszenario", "## Hochschulszenario, weitere Bedingungen"):
        assert heading in text
    assert "Richtung gleich in" in text and "resolution ibm360" in text

    import pandas as pd

    exact = pd.read_csv(tmp_path / "analysis" / "ff3_reference_runs.csv")
    ibm = pd.read_csv(other / "ff3_reference_runs.csv")
    assert len(exact) == len(ibm) and list(exact.condition) == list(ibm.condition)
    # the two arithmetics decide ties differently, so some of the 108 situations must differ
    d1 = lambda df: df[df.condition == "D_hierarchical"]["by_resolution"].to_numpy()  # noqa: E731
    assert (d1(exact) != d1(ibm)).any()
