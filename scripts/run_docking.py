"""Docking of both rule-based baselines against the published reference data.

Reads the reference workbook (sheet ``Daten_long``), runs the ports and writes one long table
with the published value, the port's value, the deviation and a status per reference figure.

FORTRAN port (Cohen, March & Olsen 1972): the 324 situations are run per arithmetic backend and
every quantity of the paper that the workbook holds is computed from the run histories:

  Tab. 1   resolution share by load x access structure (pooled over choices made)
  Tab. 2   KT, KX, KY means and flight-or-oversight share by load
  Tab. 3   share of problems solved by importance x arrival (hierarchical access only)
  Tab. 4   flight-or-oversight share by choice importance x arrival (hierarchical access or
           hierarchical decision structure)
  S. 11    share of choices not made by importance group (same 180 runs)
  Tab. 5   resolution share, KT, KU, KX, KY for the twelve organization codes
  S. 9     mean KZ and KW over all 324 runs

Eight properties of the paper (S. 9 bis 11) are checked as relational targets the way the sheet
``CMO_Eigenschaften`` proposes.

NetLogo port (Fioretti, current model): the twelve BehaviorSpace experiments are run with the
given ticks and seeds and the four documented properties of the info tab are checked. Fioretti &
Lomi (2008) is a different model, so its figures are only reported next to the port's values for
the same qualitative statements, never as numerical targets.

Usage (from the repository root):

  uv run python scripts/run_docking.py --reference GCM_Referenzdaten_CMO1972_Fioretti2008.xlsx
  uv run python scripts/run_docking.py --reference ... --arithmetic exact ibm360 ibm360-nearest
  uv run python scripts/run_docking.py --reference ... --netlogo-ticks 50000 --netlogo-seeds 30
  uv run python scripts/run_docking.py --reference ... --skip-netlogo

Output (``data/docking/``):
  fortran_runs_<arith>.csv        324 rows with all ten program statistics and decision styles
  fortran_choices_<arith>.csv     one row per choice and situation (importance, entry, style)
  fortran_problems_<arith>.csv    one row per problem and situation (importance, entry, solved)
  cmo_docking_<arith>.csv         long docking table against the workbook
  cmo_properties_<arith>.csv      the eight properties with the computed evidence
  netlogo_runs.csv                one row per experiment and seed
  netlogo_summary.csv             means per experiment
  netlogo_properties.csv          the four properties of the current model
  docking_report.md               everything readable, with the tolerance counts
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from gcm.fortran import data, experiments
from gcm.fortran.model import SOLVED_MARK
from gcm.fortran.parameters import FortranParameters
from gcm.fortran.structures import OrganizationalVariant
from gcm.contextual.paths import data_dir

LOAD_DE = {"light": "leicht", "moderate": "mittel", "heavy": "schwer"}
STRUCT_DE = {"unsegmented": "unsegmentiert", "hierarchical": "hierarchisch", "specialized": "spezialisiert"}
ENERGY_DE = {"important_less": "E0", "equal": "E1", "important_more": "E2"}

TOL_SHARE = 0.03  # absolute, for shares
TOL_REL = 0.05  # relative, for means and counts
TOL_COUNT_MIN = 2  # absolute floor for counts in Tab. 5


# ------------------------------------------------------------------------------------ FORTRAN
def run_fortran(arithmetic: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """324 runs: per-run statistics, per-choice and per-problem rows."""
    runs, choices, problems = [], [], []
    for cond, (choice_entry, problem_entry) in data.ENTRY_CONDITIONS.items():
        params = FortranParameters.from_entry_condition(cond, arithmetic=arithmetic)
        for v in OrganizationalVariant.all():
            model, stats = experiments.run_variant(v, params)
            hist = model.history
            key = {
                "entry_condition": cond,
                "code": v.code,
                "load": experiments._LOAD_NAMES[v.load],
                "access": v.access.value,
                "decision": v.decision.value,
                "energy": experiments._ENERGY_NAMES[v.energy],
            }
            runs.append({**key, **stats.as_dict()})
            for o in hist.outcomes:
                i = o.choice
                choices.append(
                    {
                        **key,
                        "choice": i + 1,
                        "entry_period": choice_entry[i],
                        "made": o.style is not None,
                        "period_made": o.period_made,
                        "style": o.style.value if o.style else "not made",
                        "problems_solved": len(o.problems_solved),
                    }
                )
            final = hist.problems[-1]
            for j in range(hist.problems.shape[1]):
                problems.append(
                    {
                        **key,
                        "problem": j + 1,
                        "entry_period": problem_entry[j],
                        "solved": bool(final[j] == SOLVED_MARK),
                    }
                )
    return pd.DataFrame(runs), pd.DataFrame(choices), pd.DataFrame(problems)


def _share(df: pd.DataFrame, num: str, den: str) -> float:
    d = df[den].sum()
    return float(df[num].sum() / d) if d else float("nan")


def own_values(runs: pd.DataFrame, choices: pd.DataFrame, problems: pd.DataFrame) -> dict[tuple, float]:
    """Every published quantity, keyed like the workbook: (kennzahl_code, last, zugang,
    entscheidung, energie, wichtigkeit, ankunft, org_code)."""
    out: dict[tuple, float] = {}
    runs = runs.assign(by_fo=runs["by_flight"] + runs["by_oversight"])
    loads = ["light", "moderate", "heavy"]
    structs = ["unsegmented", "hierarchical", "specialized"]

    def k(code, last="alle", zugang="alle", ent="alle", energie="alle", wicht=None, ank=None, org=None):
        return (code, last, zugang, ent, energie, wicht, ank, org)

    # Tab. 1
    for load in loads + [None]:
        for acc in structs + [None]:
            sub = runs
            if load:
                sub = sub[sub["load"] == load]
            if acc:
                sub = sub[sub["access"] == acc]
            out[k("anteil_resolution", LOAD_DE.get(load, "alle"), STRUCT_DE.get(acc, "alle"))] = _share(
                sub, "by_resolution", "choices_made"
            )
    # Tab. 2 and the text means
    for load in loads:
        sub = runs[runs["load"] == load]
        out[k("problemaktivitaet_KT", LOAD_DE[load])] = float(sub["problem_persistence"].mean())
        out[k("aktivitaet_entscheidungstraeger_KX", LOAD_DE[load])] = float(sub["dm_velocity"].mean())
        out[k("entscheidungsschwierigkeit_KY", LOAD_DE[load])] = float(sub["choice_persistence"].mean())
        out[k("anteil_flight_oversight", LOAD_DE[load])] = _share(sub, "by_fo", "choices_made")
    out[k("mittel_entscheidungen_nicht_getroffen_KZ")] = float(runs["choices_not_made"].mean())
    out[k("mittel_probleme_ungeloest_KW")] = float(runs["problems_not_solved"].mean())
    # Tab. 5
    for code, sub in runs.groupby("code"):
        out[k("anteil_resolution", org=code)] = _share(sub, "by_resolution", "choices_made")
        out[k("problemaktivitaet_KT", org=code)] = float(sub["problem_persistence"].mean())
        out[k("problemlatenz_KU", org=code)] = float(sub["problem_latency"].mean())
        out[k("aktivitaet_entscheidungstraeger_KX", org=code)] = float(sub["dm_velocity"].mean())
        out[k("entscheidungszeit_KY", org=code)] = float(sub["choice_persistence"].mean())
    # Tab. 3: hierarchical access, problems 1-10 important, early = entry period <= 5
    p = problems[problems["access"] == "hierarchical"]
    for wicht, lo, hi in (("hoch", 1, 10), ("niedrig", 11, 20)):
        for ank, early in (("früh (erste 10)", True), ("spät (letzte 10)", False)):
            sub = p[(p["problem"].between(lo, hi)) & ((p["entry_period"] <= 5) == early)]
            out[k("anteil_probleme_geloest", zugang="hierarchisch", wicht=wicht, ank=ank)] = float(sub["solved"].mean())
    # Tab. 4 and choice failures: hierarchical access or hierarchical decision structure
    c = choices[(choices["access"] == "hierarchical") | (choices["decision"] == "hierarchical")]
    made = c[c["made"]]
    both = "hierarchisch oder Entscheidung hierarchisch", "hierarchisch oder Zugang hierarchisch"
    for wicht, lo, hi in (("hoch", 1, 5), ("niedrig", 6, 10)):
        for ank, early in (("früh (erste 5)", True), ("spät (letzte 5)", False)):
            sub = made[(made["choice"].between(lo, hi)) & ((made["entry_period"] <= 5) == early)]
            out[k("anteil_flight_oversight", zugang=both[0], ent=both[1], wicht=wicht, ank=ank)] = float(
                sub["style"].isin(["flight", "oversight"]).mean()
            )
    for wicht, lo, hi in (("oberste 3", 1, 3), ("mittlere 4", 4, 7), ("unterste 3", 8, 10)):
        sub = c[c["choice"].between(lo, hi)]
        out[k("anteil_wahlausfaelle_KZ", zugang=both[0], ent=both[1], wicht=wicht)] = float((~sub["made"]).mean())
    return out


def load_reference(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Daten_long", header=None)
    hdr_row = raw.index[raw.iloc[:, 0] == "id"][0]
    df = pd.read_excel(path, sheet_name="Daten_long", header=hdr_row)
    df = df[df["id"].notna()].copy()
    return df


def _clean(x) -> str | None:
    """Workbook cell as a key part: empty cells (None, NaN, pandas NA) become ``None``."""
    if x is None or (isinstance(x, float) and np.isnan(x)) or str(x) in ("nan", "<NA>", ""):
        return None
    return str(x)


def ref_key(r: pd.Series) -> tuple:
    org = _clean(r["org_code"])
    if org is not None:  # Tab. 5 rows also list the factor levels; the code is the key
        return (r["kennzahl_code"], "alle", "alle", "alle", "alle", None, None, org.split(".")[0].zfill(4))
    return (
        r["kennzahl_code"],
        _clean(r["last"]) or "alle",
        _clean(r["zugang"]) or "alle",
        _clean(r["entscheidung"]) or "alle",
        _clean(r["energie"]) or "alle",
        _clean(r["wichtigkeit"]),
        _clean(r["ankunft"]),
        None if org is None else org.split(".")[0].zfill(4),
    )


def dock_cmo(ref: pd.DataFrame, own: dict[tuple, float]) -> pd.DataFrame:
    rows = []
    for _, r in ref[ref["quelle"] == "Cohen_March_Olsen_1972"].iterrows():
        key = ref_key(r)
        pub = float(r["wert"])
        mine = own.get(key)
        is_share = r["kennzahl_code"].startswith("anteil")
        if mine is None or np.isnan(mine):
            status, dev, tol = "nicht berechnet", float("nan"), float("nan")
        else:
            dev = mine - pub
            if is_share:
                tol = TOL_SHARE
                exact = abs(dev) <= 0.005
            else:
                tol = max(TOL_REL * abs(pub), TOL_COUNT_MIN if r["fundstelle"].startswith("Tab. 5") else 0.05)
                exact = abs(dev) <= 0.5 if abs(pub) >= 10 else abs(dev) <= 0.05
            status = "identisch im Rahmen der Rundung" if exact else ("innerhalb Toleranz" if abs(dev) <= tol else "Abweichung")
        rows.append(
            {
                "id": r["id"],
                "fundstelle": r["fundstelle"],
                "kennzahl_code": r["kennzahl_code"],
                "last": key[1],
                "zugang": key[2],
                "entscheidung": key[3],
                "energie": key[4],
                "wichtigkeit": key[5],
                "ankunft": key[6],
                "org_code": key[7],
                "publiziert": pub,
                "port": None if mine is None else round(mine, 4),
                "abweichung": None if mine is None else round(dev, 4),
                "abweichung_rel": None if mine is None or pub == 0 else round(dev / abs(pub), 4),
                "toleranz": tol,
                "status": status,
                "aggregation": r["aggregation"],
            }
        )
    return pd.DataFrame(rows)


def properties_cmo(runs: pd.DataFrame, choices: pd.DataFrame, problems: pd.DataFrame, own: dict) -> pd.DataFrame:
    t1 = experiments.table_1(runs)
    loads = ["light", "moderate", "heavy"]
    rows = []
    # 1
    above = [(l, a) for l in t1.index for a in t1.columns if t1.loc[l, a] >= 0.5]
    expected = {("light", "all"), ("light", "hierarchical"), ("light", "specialized"),
                ("moderate", "specialized"), ("heavy", "specialized"), ("all", "specialized")}
    rows.append({"nr": 1, "evidence": f"cells >= 0.5: {above}", "expected": sorted(expected),
                 "verdict": "bestätigt" if set(above) <= expected | {("light", "unsegmented")} and set(above) >= expected - {("light", "unsegmented")} else "abweichend"})
    # 2
    g = runs.groupby("load")
    monot = {m: list(g[m].mean().reindex(loads).round(1)) for m in ("problem_persistence", "dm_velocity", "choice_persistence")}
    fo = [round(_share(runs[runs["load"] == l], "by_flight", "choices_made") + _share(runs[runs["load"] == l], "by_oversight", "choices_made"), 3) for l in loads]
    ok = all(v[0] < v[1] < v[2] for v in monot.values())
    stable = runs[(runs["access"] == "unsegmented") & (runs["decision"] == "specialized")].groupby("load")[["choice_persistence", "by_resolution"]].mean().round(2)
    rows.append({"nr": 2, "evidence": f"means by load {monot}; flight/oversight {fo}; unsegmented access x specialized decision: {stable.to_dict()}",
                 "expected": "KT, KX, KY increase with load (flight/oversight not monotone even in the paper)",
                 "verdict": "bestätigt" if ok else "teilweise"})
    # 3 verbal only
    rows.append({"nr": 3, "evidence": "verbal in the paper; not operationalised here (see FL 2008 déjà-vu indicators)", "expected": "", "verdict": "nicht geprüft"})
    # 4 sign of segmentation effects
    def mean_by(col, lvl):
        return runs[runs[col] == lvl][["problem_persistence", "problem_latency", "choice_persistence"]].mean().round(1).to_dict()
    acc = {s: mean_by("access", s) for s in ("unsegmented", "hierarchical", "specialized")}
    dec = {s: mean_by("decision", s) for s in ("unsegmented", "hierarchical", "specialized")}
    acc_ok = all(acc[s]["problem_persistence"] < acc["unsegmented"]["problem_persistence"] and acc[s]["problem_latency"] > acc["unsegmented"]["problem_latency"] for s in ("hierarchical", "specialized"))
    dec_ok = all(dec[s]["problem_latency"] < dec["unsegmented"]["problem_latency"] and dec[s]["problem_persistence"] > dec["unsegmented"]["problem_persistence"] for s in ("hierarchical", "specialized"))
    rows.append({"nr": 4, "evidence": f"by access {acc}; by decision {dec}",
                 "expected": "segmented access: KT down, KU up; segmented decision: KU down, KT up; KY mostly up",
                 "verdict": "bestätigt" if acc_ok and dec_ok else ("teilweise" if acc_ok or dec_ok else "abweichend")})
    # 5 interaction
    ky = runs.pivot_table(index="access", columns="decision", values="choice_persistence", aggfunc="mean").round(1)
    special = ky.loc["specialized", "unsegmented"]
    rows.append({"nr": 5, "evidence": f"mean KY access x decision: {ky.to_dict()}",
                 "expected": "specialized access with unsegmented decision decides fast although specialized access is slow otherwise",
                 "verdict": "bestätigt" if special < ky.loc["specialized"].drop("unsegmented").min() and special < ky.values.mean() else "abweichend"})
    # 6 Tab. 3 ranking
    t3 = {(w, a): round(own[("anteil_probleme_geloest", "alle", "hierarchisch", "alle", "alle", w, a, None)], 3)
          for w in ("hoch", "niedrig") for a in ("früh (erste 10)", "spät (letzte 10)")}
    low_late = t3[("niedrig", "spät (letzte 10)")]
    rows.append({"nr": 6, "evidence": f"Tab. 3 port: {t3}", "expected": "low and late clearly smallest",
                 "verdict": "bestätigt" if low_late < min(v for k_, v in t3.items() if k_ != ("niedrig", "spät (letzte 10)")) else "abweichend"})
    # 7 Tab. 4 ranking
    both = ("hierarchisch oder Entscheidung hierarchisch", "hierarchisch oder Zugang hierarchisch")
    t4 = {(w, a): round(own[("anteil_flight_oversight", "alle", both[0], both[1], "alle", w, a, None)], 3)
          for w in ("hoch", "niedrig") for a in ("früh (erste 5)", "spät (letzte 5)")}
    hi_early = t4[("hoch", "früh (erste 5)")]
    rows.append({"nr": 7, "evidence": f"Tab. 4 port: {t4}", "expected": "high and early largest",
                 "verdict": "bestätigt" if hi_early > max(v for k_, v in t4.items() if k_ != ("hoch", "früh (erste 5)")) else "abweichend"})
    # 8 U-shape of failures
    fail = {w: round(own[("anteil_wahlausfaelle_KZ", "alle", both[0], both[1], "alle", w, None, None)], 3) for w in ("oberste 3", "mittlere 4", "unterste 3")}
    rows.append({"nr": 8, "evidence": f"choice failures by importance: {fail}", "expected": "top 3 and bottom 3 above middle 4",
                 "verdict": "bestätigt" if fail["oberste 3"] > fail["mittlere 4"] < fail["unterste 3"] else "abweichend"})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------ NetLogo
def run_netlogo(ticks: int, seeds: int, workers: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from gcm.netlogo import experiments as nl
    from gcm.netlogo.parameters import behavior_space_experiments

    df = nl.run_experiments(behavior_space_experiments(), repetitions=seeds, ticks=ticks, workers=workers)
    summary = nl.summarise_experiments(df)
    pooled = df.groupby("experiment", sort=False)[["num_resolutions", "num_oversights"]].sum()
    pooled["share_resolutions_pooled"] = pooled["num_resolutions"] / (pooled["num_resolutions"] + pooled["num_oversights"])
    s = pooled["share_resolutions_pooled"]
    rows = []
    rows.append({"nr": 1, "property": "most decisions by oversight (every experiment)",
                 "evidence": {k: round(float(v), 4) for k, v in s.items()}, "verdict": "bestätigt" if (s < 0.5).all() else "abweichend"})
    flights_ok, ev = [], {}
    for base in ("Organized Anarchy", "Competent Hierarchy", "Incompetent Hierarchy"):
        ev[base] = {suf or "none": round(float(s[base + suf]), 4) for suf in ("", " P", " BP", " P+BP")}
        flights_ok.append(all(s[base + suf] > s[base] for suf in (" P", " BP", " P+BP")))
    rows.append({"nr": 2, "property": "flights raise the resolution share", "evidence": ev,
                 "verdict": "bestätigt" if all(flights_ok) else ("teilweise" if any(flights_ok) else "abweichend")})
    ev3 = {suf or "none": (round(float(s["Organized Anarchy" + suf]), 4), round(float(s["Competent Hierarchy" + suf]), 4), round(float(s["Incompetent Hierarchy" + suf]), 4)) for suf in ("", " P", " BP", " P+BP")}
    ok3 = [a > max(c, i) for a, c, i in ev3.values()]
    rows.append({"nr": 3, "property": "organized anarchy out-resolves both hierarchies (anarchy, competent, incompetent)", "evidence": ev3,
                 "verdict": "bestätigt" if all(ok3) else ("teilweise" if any(ok3) else "abweichend")})
    ok4 = [i >= 0.9 * c for _, c, i in ev3.values()]
    rows.append({"nr": 4, "property": "incompetent hierarchy at least about as efficient as competent (ratio >= 0.9)", "evidence": ev3,
                 "verdict": "bestätigt" if all(ok4) else ("teilweise" if any(ok4) else "abweichend")})
    return df, summary, pd.DataFrame(rows)


# ------------------------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", type=Path, required=True, help="GCM_Referenzdaten_*.xlsx")
    ap.add_argument("--arithmetic", nargs="+", default=["exact"], choices=["exact", "float64", "ibm360", "ibm360-nearest"])
    ap.add_argument("--netlogo-ticks", type=int, default=5000)
    ap.add_argument("--netlogo-seeds", type=int, default=4)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--skip-netlogo", action="store_true")
    ap.add_argument("--out", type=Path, default=None, help="output directory (default data/docking)")
    args = ap.parse_args()

    out = args.out or (data_dir() / "docking")
    out.mkdir(parents=True, exist_ok=True)
    ref = load_reference(args.reference)
    report = [f"# Docking report\n\nreference: `{args.reference.name}`, {len(ref)} published values\n"]

    for arith in args.arithmetic:
        t0 = time.time()
        runs, choices, problems = run_fortran(arith)
        runs.to_csv(out / f"fortran_runs_{arith}.csv", index=False)
        choices.to_csv(out / f"fortran_choices_{arith}.csv", index=False)
        problems.to_csv(out / f"fortran_problems_{arith}.csv", index=False)
        own = own_values(runs, choices, problems)
        dock = dock_cmo(ref, own)
        dock.to_csv(out / f"cmo_docking_{arith}.csv", index=False)
        props = properties_cmo(runs, choices, problems, own)
        props.to_csv(out / f"cmo_properties_{arith}.csv", index=False)
        counts = dock["status"].value_counts().to_dict()
        styles = runs[["by_resolution", "by_oversight", "by_flight"]].sum()
        report.append(f"## FORTRAN port, arithmetic `{arith}` ({time.time() - t0:.0f} s, 324 runs)\n")
        report.append(f"pooled styles: {styles.to_dict()} of {int(runs['choices_made'].sum())} choices made\n")
        report.append(f"docking status: {counts}\n")
        report.append("### Deviations\n")
        bad = dock[dock["status"] == "Abweichung"]
        report.append(bad[["id", "fundstelle", "publiziert", "port", "abweichung"]].to_markdown(index=False) if len(bad) else "none\n")
        report.append("\n### Properties\n")
        report.append(props[["nr", "verdict", "evidence"]].to_markdown(index=False))
        report.append("\n")
        print(f"[{arith}] {counts}")

    if not args.skip_netlogo:
        t0 = time.time()
        df, summary, props = run_netlogo(args.netlogo_ticks, args.netlogo_seeds, args.workers)
        df.to_csv(out / "netlogo_runs.csv", index=False)
        summary.to_csv(out / "netlogo_summary.csv")
        props.to_csv(out / "netlogo_properties.csv", index=False)
        report.append(f"## NetLogo port ({args.netlogo_ticks} ticks, {args.netlogo_seeds} seeds, {time.time() - t0:.0f} s)\n")
        report.append(summary[["num_resolutions", "num_oversights", "share_resolutions", "share_resolutions_sd", "n_runs"]].to_markdown())
        report.append("\n### Properties of the current model (info tab)\n")
        report.append(props[["nr", "verdict", "property", "evidence"]].to_markdown(index=False))
        fl = ref[ref["quelle"] == "Fioretti_Lomi_2008_JASSS"]
        report.append(f"\nFioretti & Lomi (2008) values in the workbook: {len(fl)} (different model; qualitative comparison only, "
                      f"see sheet FL_Befunde). Oversight dominance (FL Nr. 1) holds for the port: see property 1.\n")
        print(props[["nr", "verdict"]].to_string(index=False))

    (out / "docking_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"report: {out / 'docking_report.md'}")


if __name__ == "__main__":
    main()
