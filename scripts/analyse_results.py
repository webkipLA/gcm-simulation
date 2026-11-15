"""Reproduces every number and figure of chapter 4 from the files under data/.

Reads the raw LLM answers (data/llm_runs/*.jsonl), the docking results (data/docking/) and the
NetLogo transfer check (data/netlogo_llm/), and writes everything to data/analysis/:

  ff2_configs.csv            structural fidelity per model x scenario x configuration
  ff3_reference_runs.csv     FORTRAN runs (108 situations) for D0, D1, D2 and the LLM structures of
                             the reference scenarios; ff3_reference_summary.csv, ff3_reference_tests.csv
  ff3_samples_and_null.csv   30 sampled structures and the three null models (unless --null 0)
  ff3_university_*.csv       the same comparison for the university scenario (tests against the
                             expected form)
  netlogo_docking_table.csv  resolution share per BehaviorSpace experiment (mean, bootstrap interval)
  figures/abb_4_1 ... 4_5    the figures of chapter 4 (PDF and PNG)
  report.md                  the key tables in one file

Usage (from the repository root):

  uv run python scripts/analyse_results.py              # everything, null model with 200 draws
  uv run python scripts/analyse_results.py --null 0     # skip the null model (fast)
  uv run python scripts/analyse_results.py --workers 6

Runs are selected by their factors, not by file names: Gemini = gemini-3.5-flash-lite, the small
model = qwen3:4b; main configuration = prose, wording a, observer, canonical order, English,
base seed 0. Runs of run_batch.py with another --seed, of the stages university_audit and
university_np and of other models are listed in ff2_configs.csv (columns seed and thinking tell
them apart) and are never used for the FF3 comparisons and the figures. If the main model has run
logs for one configuration with several thinking settings, the one of MAIN_THINKING (minimal) is
used; for any other model the script stops and names the files.

Further university conditions are analysed when their run logs exist and are skipped otherwise:
the variants without the participation statement (stage university_np), the main model with
thinking level low, and gemini-4-argon. Each is run through the FORTRAN port and compared with the
rule-based form expected for its variant and with the main-model structure of the same variant.
They get their own section in the report, their own CSV files (ff3_university_extra_*) and the
figures abb_4_6 to abb_4_8; the existing outputs do not change.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from gcm.contextual import aggregate as agg
from gcm.contextual import compare as cp
from gcm.contextual.connectors.registry import thinking_setting
from gcm.contextual.paths import data_dir
from gcm.contextual.references import reference_matrices
from gcm.contextual.scenario import load_scenarios
from gcm.contextual.structure_io import StructureExport

GEMINI, QWEN = "gemini-3.5-flash-lite", "qwen3:4b"
ARGON = "gemini-4-argon"
# The thinking setting of the runs of the thesis. When a model has run logs for one configuration
# with several thinking settings, the comparisons and figures use this one; the others stay in
# ff2_configs.csv, where the column thinking tells them apart.
MAIN_THINKING = {GEMINI: "level=minimal"}
MAIN = dict(representation="prose", wording="a", perspective="observer", item_order="canonical", language="en")
METRICS = ["proportion_resolution", "proportion_flight_or_oversight", "problem_persistence", "problem_latency",
           "dm_velocity", "choice_persistence", "choices_not_made", "problems_not_solved"]
GERMAN = {"proportion_resolution": "Anteil Resolution", "proportion_flight_or_oversight": "Anteil Flight oder Oversight",
          "problem_persistence": "Problemaktivität KT", "problem_latency": "Problemlatenz KU",
          "dm_velocity": "Aktivität der Entscheidungsträger KX", "choice_persistence": "Entscheidungsdauer KY",
          "choices_not_made": "Nicht getroffene Entscheidungen KZ", "problems_not_solved": "Ungelöste Probleme KW"}


# ------------------------------------------------------------------------------------ loading
def load_runs(scenarios) -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(data_dir() / "llm_runs" / "*.jsonl"))):
        recs = [json.loads(line) for line in open(f, encoding="utf-8")]
        if not recs or recs[0]["connector"] == "mock":
            continue
        fac = recs[0]["factors"]
        s = scenarios.get(fac["scenario_id"])
        if s is None:
            continue
        out.append(dict(file=Path(f).name, model=recs[0]["model"], fac=fac, scen=s,
                        identity=recs[0].get("identity") or {}, est=agg.aggregate(recs, s), recs=recs))
    return out


def pick(runs, model, scenario, thinking=None, **factors):
    """The one run log of a model for a scenario and configuration. ``thinking`` names the
    thinking setting when it is not the one of the thesis runs (e.g. "level=low")."""
    want = {**MAIN, "seed": 0, **factors}  # seed 0 = the runs of the thesis; other seeds are extra samples
    hits = [r for r in runs if r["model"] == model and r["scen"].id == scenario
            and all(r["fac"].get(k) == v for k, v in want.items())]
    if thinking is not None:
        hits = [r for r in hits if thinking_setting(r["identity"]) == thinking]
    elif len(hits) > 1 and model in MAIN_THINKING:
        hits = [r for r in hits if thinking_setting(r["identity"]) == MAIN_THINKING[model]] or hits
    if len(hits) != 1:
        found = "; ".join(f"{r['file']} ({thinking_setting(r['identity']) or 'no thinking setting'})" for r in hits)
        raise LookupError(f"{model} / {scenario} / {want}: {len(hits)} matching run logs"
                          + (f": {found}. They differ in the connector settings only; keep the one that is meant "
                             f"in data/llm_runs" if hits else ""))
    return hits[0]


def pick_optional(runs, model, scenario, thinking=None, **factors):
    """Like pick, but None when no such run log exists (a condition that was not run)."""
    try:
        return pick(runs, model, scenario, thinking, **factors)
    except LookupError as exc:
        if " 0 matching run logs" in str(exc):
            return None
        raise


def export_of(run, name):
    return StructureExport.from_estimate(run["est"], run["scen"], threshold=0.5, on_missing="error", name=name)


def with_binary(exp, binary, name):
    return replace(exp, binary=np.asarray(binary, bool), probability=np.asarray(binary, float), name=name)


# ------------------------------------------------------------------------------------ FF2
def ff2_table(runs) -> pd.DataFrame:
    rows = []
    for r in runs:
        e, s, f = r["est"], r["scen"], r["fac"]
        share = e.share
        known = ~np.isnan(share)
        b = share >= 0.5
        refs = reference_matrices(*s.shape)
        dist = agg.distances(share, refs).set_index("reference")["hamming_share"].to_dict()
        target = s.target_matrix()
        kappa = agg.cohen_kappa(b, target) if (target is not None and known.all() and s.expected != "unsegmented") else np.nan
        ok = [x for x in r["recs"] if not x["error"]]
        usage = [x["usage"] or {} for x in ok]
        # Ollama, Gemini and OpenAI-compatible servers (the university API) name the counts differently
        tok_in = [u.get("prompt_eval_count", u.get("promptTokenCount", u.get("prompt_tokens"))) for u in usage]
        tok_out = [u.get("eval_count", u.get("candidatesTokenCount", u.get("completion_tokens"))) for u in usage]
        rows.append({
            "model": r["model"], "scenario": s.id, "expected": s.expected, **{k: f[k] for k in
            ("mode", "representation", "wording", "perspective", "item_order", "language", "temperature", "loops")},
            "calls": len(r["recs"]), "failed": len(r["recs"]) - len(ok), "invalid_cells": int(e.invalid.sum()),
            "permitted": int(b[known].sum()), "exact": bool(target is not None and known.all() and (b == target).all()),
            **{f"dist_{k}": round(v, 3) for k, v in dist.items()},
            "nearest": min(dist, key=dist.get), "kappa_expected": round(kappa, 3) if not np.isnan(kappa) else None,
            # undefined for a run without a single valid answer (every call failed)
            "loop_agreement": round(float(((share == 0) | (share == 1))[known].mean()), 3) if known.any() else np.nan,
            "rows_without_body": int((b.sum(axis=1) == 0).sum()), "bodies_without_row": int((b.sum(axis=0) == 0).sum()),
            "median_seconds": round(float(np.median([x["latency_s"] for x in ok])), 1) if ok else None,
            "tokens_in": round(float(np.mean([t for t in tok_in if t is not None])), 0) if any(t is not None for t in tok_in) else None,
            "tokens_out": round(float(np.mean([t for t in tok_out if t is not None])), 0) if any(t is not None for t in tok_out) else None,
            "file": r["file"],
            # appended later: what tells runs of one model and configuration apart
            "seed": f.get("seed", 0), "thinking": thinking_setting(r["identity"]),
        })
    return pd.DataFrame(rows).sort_values(["scenario", "model", "temperature", "loops"], kind="stable")


# ------------------------------------------------------------------------------------ FF3
def summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("condition", sort=False)
    return pd.DataFrame({
        "choices_made": g["choices_made"].sum(),
        "resolution": g["by_resolution"].sum() / g["choices_made"].sum(),
        "oversight": g["by_oversight"].sum() / g["choices_made"].sum(),
        "flight": g["by_flight"].sum() / g["choices_made"].sum(),
        "KT": g["problem_persistence"].mean(), "KU": g["problem_latency"].mean(), "KX": g["dm_velocity"].mean(),
        "KY": g["choice_persistence"].mean(), "KZ": g["choices_not_made"].mean(), "KW": g["problems_not_solved"].mean(),
        "resolution_L1": g["by_resolution_L1"].sum() / g["choices_made_L1"].sum(),
        "resolution_L2": g["by_resolution_L2"].sum() / g["choices_made_L2"].sum(),
    })


def holm(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    order = np.argsort(np.where(np.isfinite(p), p, np.inf))
    m = int(np.isfinite(p).sum())
    adj, running = np.full(len(p), np.nan), 0.0
    for rank, i in enumerate(order[:m]):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def tests_against(df, pairs) -> pd.DataFrame:
    out = []
    for cond, ref in pairs:
        chi = cp.style_chi_square(df, conditions=[ref, cond])
        m = cp.compare_metrics(df[df.condition.isin([ref, cond])], METRICS, ref, paired_on="situation")
        m = m[m.condition == cond].assign(reference=ref, chi2=chi.chi2, chi2_p=chi.p_value, cramers_v=chi.cramers_v)
        base = df[df.condition == ref].set_index("situation")
        here = df[df.condition == cond].set_index("situation")
        dz = []
        for metric in m.metric:
            d = (here[metric] - base[metric]).dropna()
            dz.append(d.mean() / d.std(ddof=1) if d.std(ddof=1) > 0 else np.nan)
        out.append(m.assign(dz=dz, Kennzahl=m.metric.map(GERMAN)))
    t = pd.concat(out, ignore_index=True)
    t["p_holm"] = holm(t.p_value.to_numpy())
    return t


def _run_binary(args):
    exp, binary, name = args
    df = cp.run_fortran_conditions([cp.FortranCondition(name, export=with_binary(exp, binary, name))])
    return summary(df).iloc[0].to_dict()


def null_and_samples(exp_t07, n_null, workers, seed=2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    jobs = [(exp_t07, exp_t07.sample(rng), f"sample{i}") for i in range(30)]
    D1 = reference_matrices(10, 10)["hierarchical"]
    off = [(r, c) for r in range(10) for c in range(10) if D1[r, c] and r != c]
    allc = [(r, c) for r in range(10) for c in range(10) if D1[r, c]]
    for k in (9, 25):
        for cells, label in ((off, "off"), (allc, "all")):
            for i in range(n_null):
                m = D1.copy()
                for j in rng.choice(len(cells), size=k, replace=False):
                    m[cells[j]] = False
                jobs.append((exp_t07, m, f"null_{label}_k{k}_{i}"))
        made = tries = 0
        while made < n_null and tries < 100_000:
            tries += 1
            m, removed = D1.copy(), 0
            for r in rng.permutation(9):
                n = 9 - r
                if removed + n <= k:
                    m[r, r + 1:] = False
                    removed += n
                if removed == k:
                    break
            if removed == k:
                jobs.append((exp_t07, m, f"null_rows_k{k}_{made}"))
                made += 1
    with ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
        res = list(ex.map(_run_binary, jobs, chunksize=8))
    return pd.DataFrame(res, index=[n for _, _, n in jobs])


# ------------------------------------------------------------- further university conditions
VARIANTS = (("strong", "stark", "hierarchical"), ("moderate", "mittel", "specialized"), ("weak", "schwach", "unsegmented"))
EXTRA_GROUPS = (  # key, label in the report, model, scenario suffix, thinking setting
    ("np", "ohne Teilnahmeaussage", GEMINI, "_no_participation", None),
    ("low", "Hauptmodell, Denkstufe low", GEMINI, "", "level=low"),
    ("argon", "gemini-4-argon", ARGON, "", "level=low"),
)


def extra_university_exports(runs) -> dict:
    """Exports of the further university conditions that have a run log: {(group, variant): export}."""
    out = {}
    for group, label, model, suffix, thinking in EXTRA_GROUPS:
        for key, german, _ in VARIANTS:
            run = pick_optional(runs, model, f"university_{key}_power{suffix}", thinking,
                                temperature=0.7, loops=5, mode="per_row")
            if run is not None:
                out[group, key] = export_of(run, f"{label} {german}")
    return out


def extra_university(extra: dict, uni: dict, un: pd.DataFrame):
    """Run the further conditions through the FORTRAN port.

    Returns the runs (with the rule-based forms and the main-model structures of ``un`` for
    pairing), the tests, and notes on comparisons that were left out because the two structures
    are the same matrix. A condition is compared with the form expected for its variant and with
    the main-model structure of the same variant (threshold)."""
    refs = {f"D_{getattr(k, 'value', k)}": np.asarray(m, bool) for k, m in reference_matrices(10, 10).items()}
    main_name = {key: f"Hochschule {german} (Schwelle)" for key, german, _ in VARIANTS}
    mats = {**refs, **{main_name[key]: uni[key].binary for key in uni}}
    conds, pairs, notes = [], [], []
    for (group, key), exp in extra.items():
        conds.append(cp.FortranCondition(exp.name, export=exp))
        mats[exp.name] = exp.binary
        expected = f"D_{dict((k, e) for k, _, e in VARIANTS)[key]}"
        used = []  # references whose matrix has been dealt with for this condition
        for ref in (expected, main_name[key]):
            if any((mats[ref] == mats[u]).all() for u in used):
                continue  # the same matrix as a reference already compared or noted
            if (mats[ref] == exp.binary).all():
                notes.append(f"{exp.name}: Struktur identisch mit {ref}, kein Test")
            else:
                pairs.append((exp.name, ref))
            used.append(ref)
    runs = cp.run_fortran_conditions(conds)
    base = un[un.condition.isin(list(mats))]
    both = pd.concat([base, runs], ignore_index=True)
    tests = tests_against(both, pairs) if pairs else pd.DataFrame()
    return both, tests, notes


# ------------------------------------------------------------------------------------ figures
def plot_kit(out: Path):
    """Colours, formatters and the two helpers shared by all figures."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.ticker import FuncFormatter

    surf, axis = "#ffffff", "#c3c2b7"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": axis, "axes.labelcolor": "#52514e",
                         "xtick.color": "#52514e", "ytick.color": "#52514e", "axes.titlecolor": "#0b0b0b", "axes.titlesize": 10,
                         "savefig.dpi": 300, "axes.spines.top": False, "axes.spines.right": False})
    cmap = LinearSegmentedColormap.from_list("blue", ["#f0efec", "#9ec5f4", "#3987e5", "#184f95"])
    out.mkdir(parents=True, exist_ok=True)

    def save(fig, name):
        for ext in ("pdf", "png"):
            fig.savefig(out / f"{name}.{ext}", bbox_inches="tight", facecolor=surf)
        plt.close(fig)

    def heat(ax, m, title, ticks_x, ticks_y, outline=None):
        im = ax.imshow(m, cmap=cmap, vmin=0, vmax=1)
        ax.set_xticks(np.arange(m.shape[1])); ax.set_yticks(np.arange(m.shape[0]))
        ax.set_xticks(np.arange(-.5, m.shape[1], 1), minor=True); ax.set_yticks(np.arange(-.5, m.shape[0], 1), minor=True)
        ax.grid(which="minor", color=surf, lw=1.2); ax.tick_params(which="both", length=0, labelsize=7)
        ax.set_xticklabels(ticks_x, rotation=90 if len(str(ticks_x[0])) > 3 else 0); ax.set_yticklabels(ticks_y)
        for s in ax.spines.values():
            s.set_visible(False)
        if outline is not None:
            for i, j in np.argwhere(outline):
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="#e34948", lw=1.4, zorder=5))
        ax.set_title(title, fontsize=9)
        return im

    return plt, save, heat, FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ","))


MEMBERS = {"president": "Präsidentin", "chancellor": "Kanzler", "vice_president": "Vizepräs. Studium", "dean": "Dekan",
           "full_professor": "Professorin", "junior_professor": "Juniorprof.", "research_associate": "Wiss. Mitarbeiterin",
           "faculty_officer": "Fakultätsverw.", "student_representative": "Stud. Vertretung", "student": "Student"}
BODIES = ["Senat", "Haushalt", "Berufung", "Fakultätsrat", "Studienkomm.", "Prüfungsaussch.", "Forschungsförd.",
          "Modul-AG", "Laborbeschaff.", "O-Woche"]


def extra_figures(out: Path, uni: dict, extra: dict, summ: pd.DataFrame | None) -> list[str]:
    """Figures of the further university conditions; returns the names of those written.

    Cells outlined in red are permitted or not permitted differently (threshold 0.5) than in the
    first row of the same column, which is always the main model with the participation statement."""
    plt, save, heat, comma1 = plot_kit(out)
    row_ids = uni["strong"].row_ids
    members = [MEMBERS[i] for i in row_ids]
    written = []

    def grid(rows, keys, name, width):
        fig, axs = plt.subplots(len(rows), len(keys), figsize=(width, 2.05 * len(rows) + 1.1), constrained_layout=True, squeeze=False)
        titles = {"strong": "starke Macht", "moderate": "mittlere Macht", "weak": "schwache Macht"}
        for ri, (label, exports) in enumerate(rows):
            for ci, key in enumerate(keys):
                base, exp = rows[0][1][key], exports[key]
                im = heat(axs[ri, ci], exp.probability, titles[key] if ri == 0 else "",
                          BODIES if ri == len(rows) - 1 else [""] * 10, members if ci == 0 else [""] * 10,
                          None if ri == 0 else exp.binary != base.binary)
                axs[ri, ci].title.set_fontsize(8)
            axs[ri, 0].set_ylabel(label, fontsize=8, color="#0b0b0b")
        cb = fig.colorbar(im, ax=axs, shrink=.5, pad=.01); cb.set_label("Ja-Anteil", fontsize=8)
        cb.ax.tick_params(labelsize=7); cb.ax.yaxis.set_major_formatter(comma1); cb.outline.set_visible(False)
        save(fig, name)
        written.append(name)

    def group(g):
        found = {key: extra[g, key] for key, _, _ in VARIANTS if (g, key) in extra}
        return found if len(found) == 3 else None

    np_, low, argon = group("np"), group("low"), group("argon")
    if np_:
        grid([("mit Teilnahmeaussage", uni), ("ohne Teilnahmeaussage", np_)], ("strong", "moderate", "weak"),
             "abb_4_6_hochschule_ohne_teilnahme", 7.6)
    models = [(f"{GEMINI}\nDenkstufe minimal", uni)] + ([(f"{GEMINI}\nDenkstufe low", low)] if low else []) \
        + ([(f"{ARGON}\nDenkstufe low", argon)] if argon else [])
    if len(models) > 1:
        grid(models, ("strong", "moderate"), "abb_4_7_hochschule_modelle", 5.6)
    if summ is not None:
        rows = [("D_unsegmented", "D0 unsegmentiert"), ("D_hierarchical", "D1 hierarchisch"), ("D_specialized", "D2 spezialisiert")]
        for key, german, _ in VARIANTS:
            rows.append((f"Hochschule {german} (Schwelle)", f"{german}: Hauptmodell"))
            rows += [(extra[g, key].name, f"{german}: {label}") for g, label, *_ in EXTRA_GROUPS if (g, key) in extra]
        rows = [(k, l) for k, l in rows if k in summ.index]
        from matplotlib.ticker import FuncFormatter
        styles_bar(plt, FuncFormatter(lambda v, _: f"{v * 100:.0f} %"), ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"], "#ffffff",
                   "#0b0b0b", "#c3c2b7", summ, rows, 2.5, out, "abb_4_8_hochschule_entscheidungsstile", save)
        written.append("abb_4_8_hochschule_entscheidungsstile")
    return written


def figures(out: Path, runs, ref_summary: pd.DataFrame, uni_exports: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.ticker import FuncFormatter

    ink, ink2, grid, axis, surf = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#ffffff"
    cat = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": axis, "axes.labelcolor": ink2,
                         "xtick.color": ink2, "ytick.color": ink2, "axes.titlecolor": ink, "axes.titlesize": 10,
                         "savefig.dpi": 300, "axes.spines.top": False, "axes.spines.right": False})
    pct = FuncFormatter(lambda v, _: f"{v * 100:.0f} %")
    comma1 = FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ","))
    cmap = LinearSegmentedColormap.from_list("blue", ["#f0efec", "#9ec5f4", "#3987e5", "#184f95"])
    out.mkdir(parents=True, exist_ok=True)

    def save(fig, name):
        for ext in ("pdf", "png"):
            fig.savefig(out / f"{name}.{ext}", bbox_inches="tight", facecolor=surf)
        plt.close(fig)

    def heat(ax, m, title, ticks_x, ticks_y, outline=None):
        im = ax.imshow(m, cmap=cmap, vmin=0, vmax=1)
        ax.set_xticks(np.arange(m.shape[1])); ax.set_yticks(np.arange(m.shape[0]))
        ax.set_xticks(np.arange(-.5, m.shape[1], 1), minor=True); ax.set_yticks(np.arange(-.5, m.shape[0], 1), minor=True)
        ax.grid(which="minor", color=surf, lw=1.2); ax.tick_params(which="both", length=0, labelsize=7)
        ax.set_xticklabels(ticks_x, rotation=90 if len(str(ticks_x[0])) > 3 else 0); ax.set_yticklabels(ticks_y)
        for s in ax.spines.values():
            s.set_visible(False)
        if outline is not None:
            for i, j in np.argwhere(outline):
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="#e34948", lw=1.4, zorder=5))
        ax.set_title(title, fontsize=9)
        return im

    # 4.1 NetLogo docking
    nr = data_dir() / "docking" / "netlogo_runs.csv"
    if nr.exists():
        r = pd.read_csv(nr)
        structs = [("Organized Anarchy", "Organisierte Anarchie"), ("Competent Hierarchy", "Kompetente Hierarchie"),
                   ("Incompetent Hierarchy", "Inkompetente Hierarchie")]
        flights = [("", "keine Flights", "o"), (" P", "Aufschieben (P)", "s"), (" BP", "Weiterreichen (BP)", "^"), (" P+BP", "P und BP", "D")]
        fig, ax = plt.subplots(figsize=(6.3, 3.4))
        rng = np.random.default_rng(1)
        for gi, (sk, sname) in enumerate(structs):
            for fi, (fk, fname, mk) in enumerate(flights):
                x0 = gi + (fi - 1.5) * .18
                v = r[r.experiment == sk + fk].share_resolutions.to_numpy()
                b = rng.choice(v, (4000, len(v))).mean(1)
                lo, hi = np.quantile(b, [.025, .975])
                ax.scatter(x0 + rng.uniform(-.04, .04, len(v)), v, s=6, color=cat[fi], alpha=.28, linewidths=0, zorder=2)
                ax.plot([x0, x0], [lo, hi], color=cat[fi], lw=2, solid_capstyle="round", zorder=3)
                ax.scatter([x0], [v.mean()], s=36, marker=mk, color=cat[fi], edgecolors=surf, linewidths=1.5, zorder=4,
                           label=fname if gi == 0 else None)
        ax.set_xticks(range(3)); ax.set_xticklabels([n for _, n in structs]); ax.tick_params(axis="x", length=0)
        ax.yaxis.set_major_formatter(pct); ax.set_ylabel("Anteil Resolution an allen Entscheidungen"); ax.set_ylim(0, None)
        ax.grid(axis="y", color=grid, lw=.6); ax.set_axisbelow(True)
        ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(.5, 1.13), fontsize=8, handletextpad=.3, columnspacing=1.1)
        save(fig, "abb_4_1_netlogo_docking")

    # 4.2 qwen3:4b hierarchical
    D1 = reference_matrices(10, 10)["hierarchical"]
    q00 = pick(runs, QWEN, "reference_hierarchical", temperature=0.0, loops=2, mode="per_row")["est"].share
    q07 = pick(runs, QWEN, "reference_hierarchical", temperature=0.7, loops=5, mode="per_row")["est"].share
    fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.55), constrained_layout=True)
    nums = list(range(1, 11))
    im = heat(axs[0], D1.astype(float), "D1 (Regel, Zielform)", nums, nums)
    heat(axs[1], q00, "qwen3:4b, T = 0", nums, nums, (q00 >= .5) != D1)
    heat(axs[2], q07, "qwen3:4b, T = 0,7", nums, nums, (q07 >= .5) != D1)
    for ax in axs:
        ax.set_xlabel("Gelegenheit (Rang)", fontsize=8)
    axs[0].set_ylabel("Teilnehmer (Rang)", fontsize=8)
    cb = fig.colorbar(im, ax=axs, shrink=.8, pad=.02); cb.set_label("Ja-Anteil", fontsize=8)
    cb.ax.tick_params(labelsize=7); cb.ax.yaxis.set_major_formatter(comma1); cb.outline.set_visible(False)
    save(fig, "abb_4_2_qwen_hierarchie")

    # 4.3 decision styles, reference scenarios
    rows = [("D_unsegmented", "D0 unsegmentiert"), ("D_hierarchical", "D1 hierarchisch"), ("D_specialized", "D2 spezialisiert"),
            ("gemini hier T0.7", "Gemini, hierarchische Norm"), ("qwen3:4b hier T0", "qwen3:4b, T = 0"),
            ("qwen3:4b hier T0.7", "qwen3:4b, T = 0,7"), ("qwen3:4b hier T0.7 (Ziehung)", "qwen3:4b, T = 0,7, Ziehung")]
    styles_bar(plt, pct, cat, surf, ink, axis, ref_summary, rows, 2.5, out, "abb_4_3_entscheidungsstile", save)

    # 4.4 university structures
    sc = load_scenarios()
    s = sc["university_strong_power"]
    fig, axs = plt.subplots(1, 3, figsize=(7.6, 3.4), constrained_layout=True)
    names = {"president": "Präsidentin", "chancellor": "Kanzler", "vice_president": "Vizepräs. Studium", "dean": "Dekan",
             "full_professor": "Professorin", "junior_professor": "Juniorprof.", "research_associate": "Wiss. Mitarbeiterin",
             "faculty_officer": "Fakultätsverw.", "student_representative": "Stud. Vertretung", "student": "Student"}
    bodies = ["Senat", "Haushalt", "Berufung", "Fakultätsrat", "Studienkomm.", "Prüfungsaussch.", "Forschungsförd.",
              "Modul-AG", "Laborbeschaff.", "O-Woche"]
    for ax, (key, title) in zip(axs, (("strong", "starke Macht\n(erwartet: hierarchisch)"),
                                       ("moderate", "mittlere Macht\n(erwartet: spezialisiert)"),
                                       ("weak", "schwache Macht\n(erwartet: unsegmentiert)"))):
        im = heat(ax, uni_exports[key].probability, title, bodies, [names[i] for i in s.row_ids] if key == "strong" else [""] * 10)
        ax.title.set_fontsize(8)
    cb = fig.colorbar(im, ax=axs, shrink=.6, pad=.01); cb.set_label("Ja-Anteil", fontsize=8)
    cb.ax.tick_params(labelsize=7); cb.ax.yaxis.set_major_formatter(comma1); cb.outline.set_visible(False)
    save(fig, "abb_4_4_hochschulstrukturen")

    # 4.5 NetLogo transfer check
    tr = sorted(glob.glob(str(data_dir() / "netlogo_llm" / "runs_ranked_50000t_*s.csv")))
    if tr:
        r = pd.read_csv(tr[-1])
        order = [("rule: organized anarchy", "Regel: organisierte Anarchie", 0), ("rule: competent hierarchy", "Regel: kompetente Hierarchie", 0),
                 ("rule: incompetent hierarchy", "Regel: inkompetente Hierarchie", 0), ("target: hierarchical 6x5", "Zielform hierarchisch (6 × 5)", 1),
                 ("target: specialized 6x5", "Zielform spezialisiert (6 × 5)", 1), (f"{GEMINI}: strong_power", "Gemini, starke Macht", 2),
                 (f"{GEMINI}: moderate_power", "Gemini, mittlere Macht", 2), (f"{GEMINI}: weak_power", "Gemini, schwache Macht", 2)]
        fig, ax = plt.subplots(figsize=(6.3, 3.2))
        rng = np.random.default_rng(3)
        labels = {0: "regelbasiert (Fioretti)", 1: "Zielform des Szenarios", 2: "LLM-Struktur"}
        seen = set()
        for yi, (key, label, group) in enumerate(order):
            v = r[r.condition == key].share_resolutions.to_numpy()
            ax.scatter(v, yi + rng.uniform(-.12, .12, len(v)), s=8, color=cat[group], alpha=.35, linewidths=0, zorder=2)
            ax.scatter([v.mean()], [yi], s=40, marker="D", color=cat[group], edgecolors=surf, linewidths=1.5, zorder=4,
                       label=labels[group] if group not in seen else None)
            seen.add(group)
        ax.set_yticks(range(len(order))); ax.set_yticklabels([l for _, l, _ in order]); ax.invert_yaxis()
        from matplotlib.ticker import MultipleLocator
        ax.xaxis.set_major_locator(MultipleLocator(.05)); ax.xaxis.set_major_formatter(pct)
        ax.set_xlabel("Anteil Resolution an allen Entscheidungen (je Seed)")
        ax.grid(axis="x", color=grid, lw=.6); ax.set_axisbelow(True); ax.tick_params(axis="y", length=0)
        ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(.45, 1.12), fontsize=8)
        save(fig, "abb_4_5_netlogo_transfer")


def styles_bar(plt, pct, cat, surf, ink, axis, summ, rows, divider, out, name, save):
    fig, ax = plt.subplots(figsize=(6.3, .45 * len(rows) + .8))
    for yi, (key, label) in enumerate(rows):
        left = 0
        for si, (sk, sname) in enumerate((("resolution", "Resolution"), ("oversight", "Oversight"), ("flight", "Flight"))):
            w = summ.loc[key, sk]
            ax.barh(yi, w, left=left, color=cat[si], height=.62, edgecolor=surf, linewidth=2, label=sname if yi == 0 else None)
            if w >= .1:
                ax.text(left + w / 2, yi, f"{w * 100:.1f}".replace(".", ","), ha="center", va="center", fontsize=7.5,
                        color="#ffffff" if si == 0 else ink)
            left += w
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([l for _, l in rows]); ax.invert_yaxis()
    ax.axhline(divider, color=axis, lw=.8)
    ax.xaxis.set_major_formatter(pct); ax.set_xlim(0, 1); ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Anteil an den getroffenen Entscheidungen (108 Situationen, gepoolt)")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(.5, 1.0 + .5 / len(rows)), fontsize=8)
    save(fig, name)


# ------------------------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--null", type=int, default=200, help="draws per null model (0 = skip)")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()

    out = data_dir() / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    scenarios = load_scenarios()
    runs = load_runs(scenarios)
    if not runs:
        sys.exit("no run logs under data/llm_runs")
    report = ["# Auswertung (scripts/analyse_results.py)", ""]

    ff2 = ff2_table(runs)
    ff2.to_csv(out / "ff2_configs.csv", index=False)
    report += ["## FF2: Strukturtreue je Konfiguration", "",
               ff2.drop(columns=["file"]).to_markdown(index=False), ""]
    print(f"FF2: {len(ff2)} configurations")

    # reference scenarios
    q07 = export_of(pick(runs, QWEN, "reference_hierarchical", temperature=0.7, loops=5, mode="per_row"), "qwen3:4b T0.7")
    q00 = export_of(pick(runs, QWEN, "reference_hierarchical", temperature=0.0, loops=2, mode="per_row"), "qwen3:4b T0")
    gem = export_of(pick(runs, GEMINI, "reference_hierarchical", temperature=0.7, loops=5, mode="per_row"), "gemini T0.7")
    conds = cp.fortran_reference_conditions() + [
        cp.FortranCondition("gemini hier T0.7", export=gem),
        cp.FortranCondition("qwen3:4b hier T0", export=q00),
        cp.FortranCondition("qwen3:4b hier T0.7", export=q07),
        cp.FortranCondition("qwen3:4b hier T0.7 (Ziehung)", export=q07, mode="sample"),
    ]
    ref = cp.run_fortran_conditions(conds)
    ref.to_csv(out / "ff3_reference_runs.csv", index=False)
    cols = ["by_resolution", "by_oversight", "by_flight", "problem_persistence", "choice_persistence"]
    same = (ref[ref.condition == "D_hierarchical"][cols].to_numpy() == ref[ref.condition == "gemini hier T0.7"][cols].to_numpy()).all()
    ref_summary = summary(ref)
    ref_summary.to_csv(out / "ff3_reference_summary.csv")
    ref_tests = tests_against(ref, [(c, "D_hierarchical") for c in ("qwen3:4b hier T0.7", "qwen3:4b hier T0", "qwen3:4b hier T0.7 (Ziehung)")])
    ref_tests.to_csv(out / "ff3_reference_tests.csv", index=False)
    report += ["## FF3: Referenzszenarien im FORTRAN-Port", "", f"Gemini-Struktur Lauf für Lauf identisch mit D1: {bool(same)}", "",
               ref_summary.round(3).to_markdown(), "",
               ref_tests[["condition", "reference", "Kennzahl", "mean", "baseline_mean", "difference", "diff_ci_low", "diff_ci_high",
                          "dz", "p_holm", "chi2", "chi2_p", "cramers_v"]].round(4).to_markdown(index=False), ""]
    print("FF3 reference scenarios done")

    if args.null:
        nul = null_and_samples(q07, args.null, args.workers)
        nul.to_csv(out / "ff3_samples_and_null.csv")
        groups = nul.index.str.replace(r"_\d+$", "", regex=True).str.replace(r"^sample\d+$", "samples", regex=True)
        rows = []
        for label, k in (("qwen3:4b hier T0.7", 25), ("qwen3:4b hier T0", 9)):
            q = ref_summary.loc[label]
            for g in (f"null_off_k{k}", f"null_all_k{k}", f"null_rows_k{k}"):
                sub = nul[groups == g]
                rows.append({"structure": label, "null": g, **{c: f"{q[c]:.3f} (pct {100 * (sub[c] < q[c]).mean():.0f}; null {sub[c].mean():.3f})"
                                                              for c in ("resolution", "flight", "KT", "KX", "KY")}})
        sm = nul[groups == "samples"]
        report += ["## Nullmodell und Ziehungen", "", pd.DataFrame(rows).to_markdown(index=False), "",
                   f"30 Ziehungen: Resolution {sm.resolution.min():.3f} bis {sm.resolution.max():.3f} (Mittel {sm.resolution.mean():.3f})", ""]
        print("null model done")

    # university scenario
    uni = {}
    for key in ("strong", "moderate", "weak"):
        uni[key] = export_of(pick(runs, GEMINI, f"university_{key}_power", temperature=0.7, loops=5, mode="per_row"), f"Hochschule {key}")
    conds = cp.fortran_reference_conditions() + [
        cp.FortranCondition("Hochschule stark (Schwelle)", export=uni["strong"]),
        cp.FortranCondition("Hochschule stark (Ziehung)", export=uni["strong"], mode="sample"),
        cp.FortranCondition("Hochschule mittel (Schwelle)", export=uni["moderate"]),
        cp.FortranCondition("Hochschule mittel (Ziehung)", export=uni["moderate"], mode="sample"),
        cp.FortranCondition("Hochschule schwach (Schwelle)", export=uni["weak"]),
    ]
    un = cp.run_fortran_conditions(conds)
    un.to_csv(out / "ff3_university_runs.csv", index=False)
    un_summary = summary(un)
    un_summary.to_csv(out / "ff3_university_summary.csv")
    un_tests = tests_against(un, [("Hochschule stark (Schwelle)", "D_hierarchical"), ("Hochschule stark (Ziehung)", "D_hierarchical"),
                                  ("Hochschule mittel (Schwelle)", "D_specialized"), ("Hochschule mittel (Ziehung)", "D_specialized")])
    un_tests.to_csv(out / "ff3_university_tests.csv", index=False)
    report += ["## FF3: Hochschulszenario im FORTRAN-Port", "",
               "Entartung: " + "; ".join(f"{k}: {v.degenerate}" for k, v in uni.items()), "",
               un_summary.round(3).to_markdown(), "",
               un_tests[["condition", "reference", "Kennzahl", "mean", "baseline_mean", "difference", "diff_ci_low", "diff_ci_high",
                         "dz", "p_holm", "chi2", "chi2_p", "cramers_v"]].round(4).to_markdown(index=False), ""]
    print("FF3 university scenario done")

    # further university conditions (only those that have been run)
    extra = extra_university_exports(runs)
    extra_summary = None
    if extra:
        ex, ex_tests, notes = extra_university(extra, uni, un)
        ex.to_csv(out / "ff3_university_extra_runs.csv", index=False)
        extra_summary = summary(ex)
        extra_summary.to_csv(out / "ff3_university_extra_summary.csv")
        ex_tests.to_csv(out / "ff3_university_extra_tests.csv", index=False)
        cols = ["condition", "reference", "Kennzahl", "mean", "baseline_mean", "difference", "diff_ci_low", "diff_ci_high",
                "dz", "p_holm", "chi2", "chi2_p", "cramers_v"]
        report += ["## FF3: Hochschulszenario, weitere Bedingungen im FORTRAN-Port", "",
                   "Schwelle 0,5, 108 Situationen je Bedingung. Verglichen wird mit der für die Variante erwarteten Reinform und "
                   "mit der Struktur des Hauptmodells (Denkstufe minimal, mit Teilnahmeaussage) derselben Variante. "
                   "Die Holm-Korrektur umfasst alle Tests dieses Abschnitts.", "",
                   "Entartung: " + "; ".join(f"{v.name}: {v.degenerate}" for v in extra.values()), "",
                   extra_summary.round(3).to_markdown(), ""]
        report += ([ex_tests[cols].round(4).to_markdown(index=False), ""] if len(ex_tests) else [])
        report += (["Ohne Test: " + "; ".join(notes), ""] if notes else [])
        print(f"FF3 further university conditions done ({len(extra)})")

    # NetLogo docking table
    nr = data_dir() / "docking" / "netlogo_runs.csv"
    if nr.exists():
        r = pd.read_csv(nr)
        rng = np.random.default_rng(0)
        rows = []
        for e, s in r.groupby("experiment", sort=False):
            x = s.share_resolutions.to_numpy()
            b = rng.choice(x, (4000, len(x))).mean(1)
            rows.append({"experiment": e, "mean": x.mean(), "ci_low": np.quantile(b, .025), "ci_high": np.quantile(b, .975),
                         "min": x.min(), "max": x.max(), "resolutions": s.num_resolutions.mean(), "oversights": s.num_oversights.mean()})
        nd = pd.DataFrame(rows)
        nd.to_csv(out / "netlogo_docking_table.csv", index=False)
        report += ["## NetLogo-Docking", "", nd.round(4).to_markdown(index=False), ""]

    figures(out / "figures", runs, ref_summary, uni)
    if extra:
        extra_figures(out / "figures", uni, extra, extra_summary)
    (out / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"done: {out}")


if __name__ == "__main__":
    main()
