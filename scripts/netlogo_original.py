"""Run the original NetLogo model without its interface and compare it with the Python port.

The docking of the NetLogo port so far is relational: the port reproduces the four properties the
model documents. This script adds the numerical side. It needs a NetLogo installation (7.0.4 or
later, the version the model file was saved with); nothing of NetLogo is bundled here.

Two steps:

  prepare   reads the model file and writes a copy whose BehaviorSpace experiments are ready for a
            headless run, plus the commands that run them. The model code is copied byte for byte;
            only the block of experiments is replaced. The copy differs from the original in three
            points, all of them about bookkeeping and none about the model:
              - repetitions per experiment (1,000 in the file, 30 here by default),
              - every experiment reports the same 13 quantities (four experiments of the file have
                no metrics and write text files instead),
              - print? is off, so no text files are written.

  compare   reads the result tables NetLogo wrote, checks the four properties on the original and
            compares every experiment with the port's runs (data/docking/netlogo_runs.csv, written
            by run_docking.py): means with bootstrap intervals, and a two-sample
            Kolmogorov-Smirnov and a Mann-Whitney test per experiment and quantity, Holm-adjusted.

Usage (from the repository root):

  uv run python scripts/netlogo_original.py prepare --model path/to/GarbageCan_simplified17.nlogox
  uv run python scripts/netlogo_original.py prepare --model ... --ticks 2000 --repetitions 2 --out data/netlogo_original_test
  (then run data/netlogo_original/run_original.ps1 on Windows or run_original.sh elsewhere)
  uv run python scripts/netlogo_original.py compare

A test that finds no difference does not show that two distributions are the same. The report
therefore also gives the size of every difference, so that the reader can judge it.

Output in data/netlogo_original/: the model copy, the run scripts, tables/<experiment>.csv
(written by NetLogo), original_runs.csv, comparison.csv, properties.csv and report.md.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
from scipy import stats

from gcm.contextual.paths import data_dir

METRICS = [
    "num-oversights", "num-resolutions", "num-oversights-high", "num-resolutions-high", "num-oversights-low",
    "num-resolutions-low", "num-blocked-oversights", "num-blocked-resolutions", "ave-duration-blocked",
    "num-postponements", "ave-duration-postponed", "num-buck-passings", "ave-duration-passed",
]
COMPARED = ["share_resolutions", "num_resolutions", "num_oversights", "num_postponements", "num_buck_passings",
            "ave_duration_blocked"]
BLOCK = re.compile(r"<experiments>.*</experiments>", re.DOTALL)


def attr(value: str) -> str:
    """An XML attribute value in double quotes, written the way NetLogo writes it (&quot; inside)."""
    return '"' + escape(value, {'"': "&quot;"}) + '"'


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name.replace("+", " and ")).strip("_")


# ------------------------------------------------------------------------------------ prepare
def experiments_of(model_text: str) -> list[tuple[str, dict[str, str]]]:
    """Names and constants of the BehaviorSpace experiments in a .nlogox file."""
    found = BLOCK.search(model_text)
    if not found:
        raise ValueError("the model file has no <experiments> block")
    out = []
    for exp in ET.fromstring(found.group(0)).iter("experiment"):
        constants = {}
        for vs in exp.iter("enumeratedValueSet"):
            values = [v.get("value") for v in vs.iter("value")]
            if len(values) != 1:
                raise ValueError(f"experiment {exp.get('name')!r}: {vs.get('variable')} has {len(values)} values; "
                                 "only experiments with one value per variable are supported")
            constants[vs.get("variable")] = values[0]
        out.append((exp.get("name"), constants))
    return out


def experiments_block(experiments, repetitions: int, ticks: int | None) -> str:
    """The <experiments> block in the layout NetLogo 7 writes, with the same metrics everywhere."""
    lines = ["<experiments>"]
    for name, constants in experiments:
        constants = {k: v for k, v in constants.items() if k != "print?"}
        constants = {"print?": "false", **constants}  # no text files
        if ticks is not None:
            constants["stop-at"] = str(ticks)
        lines += [f'    <experiment name={attr(name)} repetitions="{repetitions}" sequentialRunOrder="true" runMetricsEveryStep="false">',
                  "      <setup>setup</setup>", "      <go>go</go>", "      <metrics>"]
        lines += [f"        <metric>{escape(m)}</metric>" for m in METRICS]
        lines += ["      </metrics>", "      <constants>"]
        for variable, value in constants.items():
            lines += [f"        <enumeratedValueSet variable={attr(variable)}>",
                      f"          <value value={attr(value)}></value>", "        </enumeratedValueSet>"]
        lines += ["      </constants>", "    </experiment>"]
    lines.append("  </experiments>")
    return "\n".join(lines)


def prepare(model: Path, out: Path, repetitions: int, ticks: int | None, threads: int) -> None:
    text = model.read_text(encoding="utf-8")
    experiments = experiments_of(text)
    copy = BLOCK.sub(lambda _: experiments_block(experiments, repetitions, ticks), text)
    assert BLOCK.sub("", copy) == BLOCK.sub("", text), "only the experiments block may change"
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(exist_ok=True)
    target = out / (model.stem + "_headless.nlogox")
    target.write_text(copy, encoding="utf-8")
    names = [name for name, _ in experiments]
    stop = experiments_of(copy)[0][1].get("stop-at")

    ps = ["# Runs the BehaviorSpace experiments of the model copy without the NetLogo interface.",
          "# Usage:  .\\run_original.ps1            (looks for NetLogo under C:\\Program Files)",
          '#         .\\run_original.ps1 -NetLogo "D:\\Apps\\NetLogo 7.0.4\\NetLogo_Console.exe"',
          "param([string]$NetLogo = '', [int]$Threads = " + str(threads) + ")",
          "$ErrorActionPreference = 'Stop'",
          "if (-not $NetLogo) {",
          "  $found = Get-ChildItem 'C:\\Program Files\\NetLogo*\\NetLogo_Console.exe' -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1",
          "  if (-not $found) { throw 'NetLogo_Console.exe not found. Pass its path with -NetLogo.' }",
          "  $NetLogo = $found.FullName",
          "}",
          "$here = Split-Path -Parent $MyInvocation.MyCommand.Path",
          f"$model = Join-Path $here '{target.name}'",
          "$experiments = @(" + ", ".join("'" + n + "'" for n in names) + ")",
          "foreach ($e in $experiments) {",
          "  $file = ($e -replace '\\+', ' and ') -replace '[^A-Za-z0-9]+', '_'",
          "  $table = Join-Path $here (Join-Path 'tables' ($file.Trim('_') + '.csv'))",
          "  if (Test-Path $table) { Write-Host \"skip $e (table exists)\"; continue }",
          "  Write-Host \"$(Get-Date -Format HH:mm:ss)  $e\"",
          "  & $NetLogo --headless --model $model --experiment $e --threads $Threads --table $table",
          "  if ($LASTEXITCODE -ne 0) { throw \"NetLogo ended with code $LASTEXITCODE in experiment $e\" }",
          "}",
          "Write-Host 'done. Next: uv run python scripts/netlogo_original.py compare'"]
    (out / "run_original.ps1").write_text("\r\n".join(ps) + "\r\n", encoding="utf-8")
    sh = ["#!/bin/sh", "# usage: NETLOGO=/path/to/NetLogo_Console ./run_original.sh [threads]", "set -e",
          'here=$(cd "$(dirname "$0")" && pwd)', f'threads="${{1:-{threads}}}"',
          ': "${NETLOGO:?set NETLOGO to the NetLogo_Console executable}"']
    for n in names:
        sh += [f'[ -f "$here/tables/{slug(n)}.csv" ] || "$NETLOGO" --headless --model "$here/{target.name}" '
               f'--experiment "{n}" --threads "$threads" --table "$here/tables/{slug(n)}.csv"']
    (out / "run_original.sh").write_text("\n".join(sh) + "\n", encoding="utf-8")

    print(f"model copy: {target}")
    print(f"{len(names)} experiments, {repetitions} repetitions each, stop-at {stop}: {len(names) * repetitions} runs")
    for n in names:
        print("  ", n)
    print(f"run them with {out / 'run_original.ps1'} (Windows) or {out / 'run_original.sh'}; tables go to {out / 'tables'}")


# ------------------------------------------------------------------------------------ compare
def read_table(path: Path) -> pd.DataFrame:
    """One BehaviorSpace table (--table): the rows after the header line that starts with [run number]."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    start = next((i for i, r in enumerate(rows) if r and r[0].strip() == "[run number]"), None)
    if start is None:
        raise ValueError(f"{path.name}: no BehaviorSpace table header ([run number]) found")
    experiment = rows[2][0] if len(rows) > 2 and rows[2] else path.stem
    df = pd.DataFrame(rows[start + 1:], columns=[c.strip() for c in rows[start]])
    df = df[df["[run number]"].str.strip() != ""]
    out = pd.DataFrame({"experiment": experiment, "run": pd.to_numeric(df["[run number]"]), "ticks": pd.to_numeric(df["[step]"])})
    for metric in METRICS:
        if metric in df:
            out[metric.replace("-", "_")] = pd.to_numeric(df[metric], errors="coerce")  # "N/A" without hierarchy
    for variable in ("stop-at", "decision-structure", "postpone?", "buckpass?"):
        if variable in df:
            out[variable.replace("-", "_").rstrip("?")] = df[variable].str.strip().str.strip('"')
    return out.sort_values("run").reset_index(drop=True)


def with_shares(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["decisions"] = df["num_resolutions"] + df["num_oversights"]
    df["share_resolutions"] = df["num_resolutions"] / df["decisions"].where(df["decisions"] > 0)
    return df


def properties(runs: pd.DataFrame) -> pd.DataFrame:
    """The four properties the model's info tab states, on pooled resolution shares (as run_docking.py)."""
    pooled = runs.groupby("experiment", sort=False)[["num_resolutions", "num_oversights"]].sum()
    s = pooled["num_resolutions"] / (pooled["num_resolutions"] + pooled["num_oversights"])
    suffixes = ("", " P", " BP", " P+BP")
    bases = ("Organized Anarchy", "Competent Hierarchy", "Incompetent Hierarchy")
    if not all(b + x in s.index for b in bases for x in suffixes):
        return pd.DataFrame()

    def verdict(flags):
        return "bestätigt" if all(flags) else ("teilweise" if any(flags) else "abweichend")

    triple = {x or "none": tuple(round(float(s[b + x]), 4) for b in bases) for x in suffixes}
    return pd.DataFrame([
        {"nr": 1, "property": "most decisions by oversight (every experiment)", "verdict": verdict([(s < 0.5).all()]),
         "evidence": {k: round(float(v), 4) for k, v in s.items()}},
        {"nr": 2, "property": "flights raise the resolution share",
         "verdict": verdict([all(s[b + x] > s[b] for x in suffixes[1:]) for b in bases]),
         "evidence": {b: {x or "none": round(float(s[b + x]), 4) for x in suffixes} for b in bases}},
        {"nr": 3, "property": "organized anarchy out-resolves both hierarchies (anarchy, competent, incompetent)",
         "verdict": verdict([a > max(c, i) for a, c, i in triple.values()]), "evidence": triple},
        {"nr": 4, "property": "incompetent hierarchy at least about as efficient as competent (ratio >= 0.9)",
         "verdict": verdict([i >= 0.9 * c for _, c, i in triple.values()]), "evidence": triple},
    ])


def holm(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    finite = np.isfinite(p)
    order = np.argsort(np.where(finite, p, np.inf))
    adj, running, m = np.full(len(p), np.nan), 0.0, int(finite.sum())
    for rank, i in enumerate(order[:m]):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def compare_runs(original: pd.DataFrame, port: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Per experiment and quantity: both means, the difference with a bootstrap interval, two tests."""
    rng = np.random.default_rng(seed)
    rows = []
    for experiment in [e for e in original["experiment"].unique() if e in set(port["experiment"])]:
        a_all, b_all = original[original.experiment == experiment], port[port.experiment == experiment]
        for metric in COMPARED:
            a, b = a_all[metric].dropna().to_numpy(float), b_all[metric].dropna().to_numpy(float)
            if len(a) < 2 or len(b) < 2:
                continue
            boot = rng.choice(b, (4000, len(b))).mean(1) - rng.choice(a, (4000, len(a))).mean(1)
            same = np.ptp(np.concatenate([a, b])) == 0
            rows.append({
                "experiment": experiment, "metric": metric, "n_original": len(a), "n_port": len(b),
                "mean_original": a.mean(), "sd_original": a.std(ddof=1), "mean_port": b.mean(), "sd_port": b.std(ddof=1),
                "difference": b.mean() - a.mean(), "diff_ci_low": np.quantile(boot, .025), "diff_ci_high": np.quantile(boot, .975),
                "difference_rel": (b.mean() - a.mean()) / abs(a.mean()) if a.mean() else np.nan,
                "ks_p": np.nan if same else stats.ks_2samp(a, b).pvalue,
                "mannwhitney_p": np.nan if same else stats.mannwhitneyu(a, b, alternative="two-sided").pvalue,
            })
    out = pd.DataFrame(rows)
    if len(out):
        out["ks_p_holm"] = holm(out["ks_p"].to_numpy())
        out["mannwhitney_p_holm"] = holm(out["mannwhitney_p"].to_numpy())
    return out


def compare(out: Path, port_file: Path) -> None:
    tables = sorted((out / "tables").glob("*.csv"))
    if not tables:
        sys.exit(f"no tables in {out / 'tables'}; run the experiments first (prepare, then run_original)")
    original = with_shares(pd.concat([read_table(t) for t in tables], ignore_index=True))
    original.to_csv(out / "original_runs.csv", index=False)
    counts = original.groupby("experiment", sort=False).agg(runs=("run", "size"), ticks=("ticks", "max"))
    report = ["# Original NetLogo model, run headless, against the Python port", "",
              f"{len(tables)} experiments, {len(original)} runs of the original.", "",
              counts.to_markdown(), "",
              "## Original: means per experiment", "",
              original.groupby("experiment", sort=False)[["share_resolutions", "num_resolutions", "num_oversights",
                                                          "num_postponements", "num_buck_passings"]].mean().round(4).to_markdown(), ""]
    props = properties(original)
    if len(props):
        props.to_csv(out / "properties.csv", index=False)
        report += ["## Original: the four properties of the info tab", "", props[["nr", "verdict", "property", "evidence"]].to_markdown(index=False), ""]
    if not port_file.exists():
        report += [f"No comparison: `{port_file}` is missing (written by scripts/run_docking.py).", ""]
        print(f"no comparison: {port_file} is missing")
    else:
        port = with_shares(pd.read_csv(port_file))
        ticks_port, ticks_orig = sorted(port["ticks"].unique()), sorted(original["ticks"].unique())
        cmp = compare_runs(original, port)
        cmp.to_csv(out / "comparison.csv", index=False)
        report += ["## Port against original", "",
                   f"Port: `{port_file.name}`, ticks {ticks_port}; original: ticks {ticks_orig}.", ""]
        if ticks_port != ticks_orig:
            report += ["**The two were not run for the same number of ticks; counts are then not comparable.**", ""]
        if len(cmp):
            share = cmp[cmp.metric == "share_resolutions"]
            n_sig = int((cmp["ks_p_holm"] < 0.05).sum())
            report += [f"{len(cmp)} comparisons ({cmp['experiment'].nunique()} experiments x {cmp['metric'].nunique()} quantities). "
                       f"Kolmogorov-Smirnov, Holm-adjusted: {n_sig} with p < 0.05. Largest relative difference of the mean "
                       f"resolution share: {share['difference_rel'].abs().max():.1%}.", "",
                       "A test without a finding does not prove that the distributions are equal; read the differences and their intervals.", "",
                       "### Resolution share", "",
                       share.drop(columns=["metric"]).round(4).to_markdown(index=False), "",
                       "### All quantities", "", cmp.round(4).to_markdown(index=False), ""]
            print(share[["experiment", "mean_original", "mean_port", "difference", "diff_ci_low", "diff_ci_high", "ks_p_holm"]].round(4).to_string(index=False))
            print(f"{n_sig} of {len(cmp)} comparisons differ (KS, Holm, p < 0.05)")
    (out / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"report: {out / 'report.md'}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["prepare", "compare"])
    ap.add_argument("--model", type=Path, help="prepare: the original .nlogox file")
    ap.add_argument("--repetitions", type=int, default=30, help="prepare: runs per experiment (default 30, as the port's docking run)")
    ap.add_argument("--ticks", type=int, default=None, help="prepare: override stop-at, e.g. 2000 for a trial (default: as in the file, 50000)")
    ap.add_argument("--threads", type=int, default=4, help="prepare: default number of parallel runs written into the run scripts")
    ap.add_argument("--port", type=Path, default=None, help="compare: runs of the port (default data/docking/netlogo_runs.csv)")
    ap.add_argument("--out", type=Path, default=None, help="working directory (default data/netlogo_original)")
    args = ap.parse_args(argv)
    out = args.out or (data_dir() / "netlogo_original")
    if args.step == "prepare":
        if args.model is None or not args.model.exists():
            sys.exit("prepare needs --model with the path of the original .nlogox file")
        prepare(args.model, out, args.repetitions, args.ticks, args.threads)
    else:
        compare(out, args.port or (data_dir() / "docking" / "netlogo_runs.csv"))


if __name__ == "__main__":
    main()
