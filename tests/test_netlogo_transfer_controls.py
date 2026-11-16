"""The exclusion controls of the NetLogo transfer check."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from gcm.contextual.references import reference_matrices

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------- exclusion controls (run_netlogo_llm.py)
def export(rows: list[str]) -> SimpleNamespace:
    ids = ("presidium", "deans", "professors", "administration", "research_staff", "students")
    return SimpleNamespace(binary=np.array([[c == "1" for c in r] for r in rows]), row_ids=ids)


def test_exclusion_controls_are_the_expected_form_without_the_excluded_groups():
    rn = load("run_netlogo_llm")
    refs = reference_matrices(6, 5)
    exports = {
        "m: strong_power": export(["11111", "01110", "01111", "01001", "00000", "00000"]),
        "m: moderate_power": export(["00000", "01110", "00010", "01001", "00000", "00000"]),
        "m: weak_power": export(["11111"] * 6),
        "other: strong_power": export(["11111", "01110", "01111", "01001", "00001", "10000"]),  # nobody shut out
    }
    controls = rn.exclusion_controls(exports, refs)
    assert list(controls) == ["control for m: strong_power: hierarchical 6x5 without excluded groups",
                              "control for m: moderate_power: specialized 6x5 without excluded groups"]
    binary, label, target, excluded = controls["control for m: strong_power: hierarchical 6x5 without excluded groups"]
    assert (label, target, excluded) == ("m: strong_power", "target: hierarchical 6x5", ["research_staff", "students"])
    full = np.asarray(refs["hierarchical"], bool)
    assert not binary[4:].any() and (binary[:4] == full[:4]).all()  # only the excluded rows differ from the form
    assert full[4:].any()  # and the form itself does let these groups in somewhere
    binary, _, target, excluded = controls["control for m: moderate_power: specialized 6x5 without excluded groups"]
    assert target == "target: specialized 6x5" and excluded == ["presidium", "research_staff", "students"]
    assert not binary[[0, 4, 5]].any() and (binary[1:4] == np.asarray(refs["specialized"], bool)[1:4]).all()


def test_transfer_check_runs_with_the_flag_and_keeps_the_files_of_a_run_without_it(tmp_path, monkeypatch, capsys):
    rn = load("run_netlogo_llm")
    monkeypatch.setenv("GCM_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    rn.main(["llm", "--connector", "mock"])
    common = ["sim", "--connector", "mock", "--ticks", "200", "--seeds", "2", "--workers", "1"]
    rn.main(common)
    out = tmp_path / "netlogo_llm"
    plain = sorted(p.name for p in out.glob("*200t_2s*"))
    assert plain == ["report_ranked_200t_2s.md", "runs_ranked_200t_2s.csv", "styles_ranked_200t_2s.csv", "tests_ranked_200t_2s.csv"]
    before = (out / "runs_ranked_200t_2s.csv").read_bytes()
    rn.main([*common, "--exclusion-controls"])
    assert (out / "runs_ranked_200t_2s.csv").read_bytes() == before
    assert (out / "runs_ranked_200t_2s_controls.csv").exists() and (out / "report_ranked_200t_2s_controls.md").exists()
    with_flag = pd.read_csv(out / "runs_ranked_200t_2s_controls.csv")
    without = pd.read_csv(out / "runs_ranked_200t_2s.csv")
    # the conditions both runs share give the same results, seed by seed
    shared = with_flag[with_flag.condition.isin(without.condition)].reset_index(drop=True)
    pd.testing.assert_frame_equal(shared, without)
