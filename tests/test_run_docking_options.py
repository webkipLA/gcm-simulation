"""The initial requirement of a choice in the FORTRAN port as an option of the docking script."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "reference" / "GCM_Referenzdaten_CMO1972_Fioretti2008.xlsx"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------- initial requirement (run_docking.py)
@pytest.mark.skipif(not WORKBOOK.exists(), reason="reference workbook not in the checkout")
def test_initial_requirement_is_compared_and_the_default_keeps_its_files(tmp_path, capsys):
    rd = load("run_docking")
    out = tmp_path / "docking"
    rd.main(["--reference", str(WORKBOOK), "--skip-netlogo", "--initial-requirement", "1.1", "0", "--out", str(out)])
    names = sorted(p.name for p in out.iterdir())
    for stem in ("fortran_runs", "fortran_choices", "fortran_problems", "cmo_docking", "cmo_properties"):
        assert f"{stem}_exact.csv" in names and f"{stem}_exact__xerc0.csv" in names  # 1.1 keeps the old names
    table = pd.read_csv(out / "fortran_configurations.csv")
    assert list(table.configuration) == ["exact", "exact__xerc0"]
    first, other = table.iloc[0], table.iloc[1]
    # the documented state of the docking with the value of the listing
    assert (first["identisch im Rahmen der Rundung"], first["innerhalb Toleranz"], first["Abweichung"]) == (47, 33, 21)
    assert first["situations differing from the first"] == 0 and other["situations differing from the first"] > 0
    assert other["Abweichung"] > first["Abweichung"]
    changed = pd.read_csv(out / "fortran_configurations_changed_values.csv")
    assert len(changed) > 0 and {"status exact", "status exact__xerc0", "port exact", "port exact__xerc0"} <= set(changed.columns)
    assert (changed["status exact"] != changed["status exact__xerc0"]).all()
    report = (out / "docking_report.md").read_text(encoding="utf-8")
    assert "initial requirement 0" in report and "## Comparison of the FORTRAN configurations" in report


@pytest.mark.skipif(not WORKBOOK.exists(), reason="reference workbook not in the checkout")
def test_docking_without_the_option_writes_what_it_wrote_before(tmp_path):
    rd = load("run_docking")
    out = tmp_path / "docking"
    rd.main(["--reference", str(WORKBOOK), "--skip-netlogo", "--out", str(out)])
    assert sorted(p.name for p in out.iterdir()) == ["cmo_docking_exact.csv", "cmo_properties_exact.csv", "docking_report.md",
                                                     "fortran_choices_exact.csv", "fortran_problems_exact.csv", "fortran_runs_exact.csv"]
    assert "Comparison of the FORTRAN configurations" not in (out / "docking_report.md").read_text(encoding="utf-8")
    with pytest.raises(SystemExit, match="decimal"):
        rd.main(["--reference", str(WORKBOOK), "--skip-netlogo", "--initial-requirement", "viel", "--out", str(out)])
