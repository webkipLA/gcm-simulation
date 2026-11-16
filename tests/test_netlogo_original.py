"""Preparing the original NetLogo model for a headless run and reading its result tables.
NetLogo itself is not run here; its table format is written by a helper."""

from __future__ import annotations

import csv
import importlib.util
import itertools
import re
from pathlib import Path

import pandas as pd
import pytest

from gcm.netlogo import experiments as nl
from gcm.netlogo.parameters import behavior_space_experiments

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def no():
    spec = importlib.util.spec_from_file_location("netlogo_original", ROOT / "scripts" / "netlogo_original.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def constants(structure: str, postpone: str, buckpass: str, print_: bool) -> str:
    values = {"stop-at": "50000", "show-details?": "false", "number-of-participants": "100", "max-efficiency": "1",
              "decision-structure": f"&quot;{structure}&quot;", "availability-structure": f"&quot;{structure}&quot;",
              "access-structure": f"&quot;{structure}&quot;", "buckpass?": buckpass, "postpone?": postpone, "span-of-control": "2"}
    if print_:
        values = {"print?": "true", **values}
    return "\n".join(f'        <enumeratedValueSet variable="{k}">\n          <value value="{v}"></value>\n        </enumeratedValueSet>'
                     for k, v in values.items())


def experiment(name: str, structure: str, postpone: str, buckpass: str, metrics: bool) -> str:
    m = ("      <metrics>\n        <metric>num-oversights</metric>\n        <metric>num-resolutions</metric>\n      </metrics>\n"
         if metrics else "")
    return (f'    <experiment name="{name}" repetitions="1000" sequentialRunOrder="true" runMetricsEveryStep="false">\n'
            f"      <setup>setup</setup>\n      <go>go</go>\n{m}      <constants>\n"
            f"{constants(structure, postpone, buckpass, not metrics)}\n      </constants>\n    </experiment>")


# the layout of the model file: code in CDATA, widgets, then the experiments; some of them without metrics
MODEL = ('<?xml version="1.0" encoding="utf-8"?>\n<model version="NetLogo 7.0.4" snapToGrid="false">\n'
         "  <code><![CDATA[globals [ num-oversights ]\nto go\n  if (a < b and c > d) [ stop ]\nend]]></code>\n"
         '  <widgets>\n    <switch x="313" y="13" on="false" variable="print?" display="print?"></switch>\n  </widgets>\n'
         "  <experiments>\n"
         + "\n".join([experiment("Organized Anarchy", "organized anarchy", "false", "false", metrics=False),
                      experiment("Organized Anarchy P+BP", "organized anarchy", "true", "true", metrics=True),
                      experiment("Competent Hierarchy P", "competent hierarchy", "true", "false", metrics=False)])
         + "\n  </experiments>\n</model>\n")


def test_prepare_changes_the_experiments_and_nothing_else(no, tmp_path, capsys):
    model = tmp_path / "GarbageCan.nlogox"
    model.write_text(MODEL, encoding="utf-8")
    out = tmp_path / "work"
    no.main(["prepare", "--model", str(model), "--out", str(out), "--repetitions", "30", "--threads", "3"])
    copy = (out / "GarbageCan_headless.nlogox").read_text(encoding="utf-8")
    outside = lambda text: re.sub(r"<experiments>.*</experiments>", "", text, flags=re.DOTALL)  # noqa: E731
    assert outside(copy) == outside(MODEL) and "if (a < b and c > d) [ stop ]" in copy  # the code is untouched

    before, after = dict(no.experiments_of(MODEL)), dict(no.experiments_of(copy))
    assert list(after) == ["Organized Anarchy", "Organized Anarchy P+BP", "Competent Hierarchy P"]
    for name in after:
        assert after[name]["print?"] == "false"  # no text files, also where the file says true
        assert {k: v for k, v in after[name].items() if k != "print?"} == {k: v for k, v in before[name].items() if k != "print?"}
    assert after["Competent Hierarchy P"]["decision-structure"] == '"competent hierarchy"'
    assert copy.count('repetitions="30"') == 3 and 'repetitions="1000"' not in copy
    assert copy.count("<metric>") == 3 * len(no.METRICS)  # the same quantities for every experiment
    assert 'value="&quot;competent hierarchy&quot;"' in copy  # written the way NetLogo writes it

    ps = (out / "run_original.ps1").read_text(encoding="utf-8")
    assert "'Organized Anarchy P+BP'" in ps and "--headless --model $model --experiment $e --threads $Threads --table $table" in ps
    assert "[int]$Threads = 3" in ps
    sh = (out / "run_original.sh").read_text(encoding="utf-8")
    assert sh.count("--headless") == 3 and 'tables/Organized_Anarchy_P_and_BP.csv' in sh
    assert (out / "tables").is_dir()
    assert "3 experiments, 30 repetitions each, stop-at 50000: 90 runs" in capsys.readouterr().out


def test_prepare_can_shorten_the_runs_for_a_trial(no, tmp_path):
    model = tmp_path / "m.nlogox"
    model.write_text(MODEL, encoding="utf-8")
    no.main(["prepare", "--model", str(model), "--out", str(tmp_path / "w"), "--ticks", "2000", "--repetitions", "2"])
    after = dict(no.experiments_of((tmp_path / "w" / "m_headless.nlogox").read_text(encoding="utf-8")))
    assert {c["stop-at"] for c in after.values()} == {"2000"}
    with pytest.raises(SystemExit, match="--model"):
        no.main(["prepare", "--out", str(tmp_path / "x")])


def write_table(path: Path, name: str, runs: pd.DataFrame, hierarchy: bool) -> None:
    """A BehaviorSpace table as NetLogo writes it with --table (six header lines, then one row per run)."""
    header = ["[run number]", "print?", "stop-at", "decision-structure", "postpone?", "buckpass?", "[step]",
              "num-oversights", "num-resolutions", "num-oversights-high", "num-resolutions-high", "num-oversights-low",
              "num-resolutions-low", "num-blocked-oversights", "num-blocked-resolutions", "ave-duration-blocked",
              "num-postponements", "ave-duration-postponed", "num-buck-passings", "ave-duration-passed"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerows([["BehaviorSpace results (NetLogo 7.0.4)", "Table version 2.0"], ["GarbageCan_headless.nlogox"], [name],
                     ["11/16/2026 10:00:00:000 +0100"], ["min-pxcor", "max-pxcor", "min-pycor", "max-pycor"], ["0", "49", "0", "49"], header])
        for i, r in enumerate(runs.itertuples(), start=1):
            high = [r.num_oversights_high, r.num_resolutions_high, r.num_oversights_low, r.num_resolutions_low] if hierarchy else ["N/A"] * 4
            w.writerow([i, "false", r.ticks, '"x"', "true", "false", r.ticks, r.num_oversights, r.num_resolutions, high[0], high[1],
                        high[2], high[3], r.num_blocked_oversights, r.num_blocked_resolutions, r.ave_duration_blocked,
                        r.num_postponements, r.ave_duration_postponed, r.num_buck_passings, r.ave_duration_passed])


@pytest.fixture(scope="module")
def port_runs():
    """Two independent sets of short runs of the port: one stands in for the original."""
    exps = behavior_space_experiments()
    a = nl.run_experiments(exps, repetitions=3, ticks=250, seed0=0, workers=1)
    b = nl.run_experiments(exps, repetitions=3, ticks=250, seed0=100, workers=1)
    return a, b


def test_tables_are_read_and_compared_with_the_port(no, port_runs, tmp_path, capsys):
    port, stand_in = port_runs
    out = tmp_path / "work"
    (out / "tables").mkdir(parents=True)
    for name, runs in stand_in.groupby("experiment", sort=False):
        write_table(out / "tables" / f"{no.slug(name)}.csv", name, runs, hierarchy="Anarchy" not in name)
    port_file = tmp_path / "netlogo_runs.csv"
    port.to_csv(port_file, index=False)
    no.main(["compare", "--out", str(out), "--port", str(port_file)])

    original = pd.read_csv(out / "original_runs.csv")
    assert len(original) == 36 and set(original.experiment) == set(behavior_space_experiments())
    merged = original.sort_values(["experiment", "run"]).reset_index(drop=True)
    expected = stand_in.sort_values(["experiment", "seed"]).reset_index(drop=True)
    for column in ("num_resolutions", "num_oversights", "num_postponements", "num_buck_passings"):
        assert (merged[column] == expected[column]).all()
    assert merged.loc[merged.experiment == "Organized Anarchy", "num_oversights_high"].isna().all()  # "N/A" without a hierarchy

    cmp = pd.read_csv(out / "comparison.csv")
    assert cmp["experiment"].nunique() == 12 and set(cmp.metric) <= set(no.COMPARED)
    row = cmp[(cmp.experiment == "Organized Anarchy P+BP") & (cmp.metric == "num_oversights")].iloc[0]
    a = stand_in[stand_in.experiment == "Organized Anarchy P+BP"].num_oversights
    b = port[port.experiment == "Organized Anarchy P+BP"].num_oversights
    assert row.mean_original == pytest.approx(a.mean()) and row.mean_port == pytest.approx(b.mean())
    assert row.difference == pytest.approx(b.mean() - a.mean()) and row.diff_ci_low <= row.difference <= row.diff_ci_high
    assert cmp["ks_p_holm"].dropna().between(0, 1).all()
    assert len(pd.read_csv(out / "properties.csv")) == 4
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "## Port against original" in report and "does not prove that the distributions are equal" in report


def test_the_same_runs_on_both_sides_show_no_difference(no, port_runs, tmp_path):
    port, _ = port_runs
    out = tmp_path / "work"
    (out / "tables").mkdir(parents=True)
    for name, runs in itertools.islice(port.groupby("experiment", sort=False), 3):
        write_table(out / "tables" / f"{no.slug(name)}.csv", name, runs, hierarchy=False)
    port_file = tmp_path / "p.csv"
    port.to_csv(port_file, index=False)
    no.main(["compare", "--out", str(out), "--port", str(port_file)])
    cmp = pd.read_csv(out / "comparison.csv")
    assert cmp["experiment"].nunique() == 3 and (cmp["difference"].abs() < 1e-9).all()
    assert not (out / "properties.csv").exists()  # the properties need all twelve experiments
    assert not (cmp["ks_p_holm"] < 0.05).any()


def test_compare_needs_tables_and_reports_other_tick_counts(no, port_runs, tmp_path):
    with pytest.raises(SystemExit, match="no tables"):
        no.main(["compare", "--out", str(tmp_path / "empty")])
    port, stand_in = port_runs
    out = tmp_path / "work"
    (out / "tables").mkdir(parents=True)
    runs = stand_in[stand_in.experiment == "Competent Hierarchy"].assign(ticks=999)
    write_table(out / "tables" / "Competent_Hierarchy.csv", "Competent Hierarchy", runs, hierarchy=True)
    port_file = tmp_path / "p.csv"
    port.to_csv(port_file, index=False)
    no.main(["compare", "--out", str(out), "--port", str(port_file)])
    assert "not run for the same number of ticks" in (out / "report.md").read_text(encoding="utf-8")
