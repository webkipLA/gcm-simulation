"""Transfer check in the NetLogo port: LLM decision structures for the role scenario.

The FORTRAN port is the main test bed of the substitution. This script carries the substitution
over to the agent-based port with the role scenario (``university_roles``: 6 groups of members x
5 kinds of bodies, three variants along administrative power x problem interrelation).

Two steps, each restartable (answers are cached, nothing is asked twice):

  llm   asks a model about the three variants with the conventions of run_batch.py
        (per_row, 5 loops, temperature 0.7, seed 0) and exports the structures.
  sim   runs the NetLogo port with every structure under the same seeds and compares it with
        rule-based structures: the unrestricted model (organized anarchy), the competent and the
        incompetent hierarchy (decision structure only) and the expected forms of the scenario
        (hierarchical and specialized 6 x 5 matrices, expanded with the same role assignment).
        Availability and access structure stay unrestricted, so only the decision structure
        differs between the conditions. Flights (postponement and buck-passing) are on, as in the
        model's defaults.

Usage (from the repository root):

  uv run python scripts/run_netlogo_llm.py llm --connector gemini/gemini-3.5-flash-lite
  uv run python scripts/run_netlogo_llm.py sim --connector gemini/gemini-3.5-flash-lite --dry-run
  uv run python scripts/run_netlogo_llm.py sim --connector gemini/gemini-3.5-flash-lite --ticks 50000 --seeds 10 --workers 6

  --connector may be given several times for sim (e.g. Gemini and qwen3:4b);
  --mapping ranked|random|inverse sets how groups map onto the abilities drawn at setup
  (default ranked: the first group gets the ablest participants).

Output in data/netlogo_llm/: structures.md (matrices, distances, row sums), runs.csv (one row per
condition and seed), styles.csv, tests.csv (paired by seed, Holm-adjusted), report.md.
Structures are also saved under data/structures/roles/.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from gcm.contextual import aggregate as agg
from gcm.contextual import compare as cp
from gcm.contextual.cache import DiskCache
from gcm.contextual.connectors import MockConnector, available_connectors
from gcm.contextual.experiment import ExperimentConfig, run_experiment
from gcm.contextual.netlogo_adapter import RoleAssignment
from gcm.contextual.paths import cache_dir, data_dir, runs_dir, structures_dir
from gcm.contextual.references import reference_matrices
from gcm.contextual.scenario import load_scenarios
from gcm.contextual.structure_io import StructureExport
from gcm.netlogo.parameters import NetLogoParameters, Structure

VARIANTS = ["university_roles_strong_power", "university_roles_moderate_power", "university_roles_weak_power"]
CONFIG = dict(mode="per_row", loops=5, temperature=0.7, seed=0)  # as the core stage of run_batch.py
METRICS = [
    "share_resolutions",
    "decisions",
    "num_resolutions",
    "num_oversights",
    "flights",
    "ave_duration_blocked",
    "resolution_share_L1",
    "resolution_share_L2",
    "decisions_L1",
    "decisions_L2",
]


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", text).strip("-")


def connector_factory(name: str):
    if name == "mock":
        return None
    factories = available_connectors()
    if name not in factories:
        sys.exit(f"connector {name!r} not configured; available: {sorted(factories) or 'none (check .env)'}")
    return factories[name]


def make_connector(name, factory, scenario, cfg):
    if factory is None:
        return MockConnector.for_scenario(scenario, noise=0.1, seed=cfg.seed)
    return factory()


def structure_report(scenario, estimate, title: str) -> str:
    """Yes shares, binary matrix, distances and row sums as Markdown."""
    share = estimate.share
    binary = share >= 0.5
    refs = reference_matrices(*scenario.shape)
    dist = agg.distances(share, refs).set_index("reference")["hamming_share"]
    lines = [f"### {title}", "", f"expected form: {scenario.expected}; invalid answers: {int(estimate.invalid.sum())}, failed calls: {int(estimate.errors.sum())}", ""]
    header = "| | " + " | ".join(scenario.col_ids) + " | permitted |"
    lines += [header, "|" + "---|" * (len(scenario.col_ids) + 2)]
    for r, rid in enumerate(scenario.row_ids):
        cells = " | ".join(f"{share[r, c]:.1f}" for c in range(share.shape[1]))
        lines.append(f"| {rid} | {cells} | {int(binary[r].sum())} |")
    lines += ["", "Hamming share to the rule-based 6 x 5 forms: " + ", ".join(f"{k} {v:.2f}" for k, v in dist.items()),
              f"nearest: {dist.idxmin()}; density {binary.mean():.2f}; rows with exactly one body: {int((binary.sum(axis=1) == 1).sum())} of {binary.shape[0]}; "
              f"bodies nobody may enter: {[scenario.col_ids[c] for c in np.flatnonzero(~binary.any(axis=0))]}", ""]
    return "\n".join(lines)


def collect(scenarios, connectors, cache, *, ask: bool):
    """Run (ask=True) or read from the cache (ask=False) every variant for every connector."""
    out = {}
    for name in connectors:
        factory = connector_factory(name)
        for sid in VARIANTS:
            s = scenarios[sid]
            cfg = ExperimentConfig(sid, **CONFIG)
            res = run_experiment(s, cfg, make_connector(name, factory, s, cfg), cache=cache,
                                 log_dir=runs_dir() if ask else None, cache_only=not ask)
            if not ask and res.n_missing:
                sys.exit(f"{name} / {sid}: {res.n_missing} answers missing; run the llm step first")
            ok = sum(1 for r in res.records if not r["error"])
            if ask:
                print(f"  {name} {sid}: {res.n_new} new, {res.n_cached} cached, {res.n_errors} failed", flush=True)
                if res.n_new >= 5 and ok == 0:
                    sys.exit("every call failed (quota, key or connection?); stopping, start again later")
            est = agg.aggregate(res.records, s, label=f"{name} | {sid}")
            out[(name, sid)] = (s, est)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["llm", "sim"])
    ap.add_argument("--connector", action="append", required=True)
    ap.add_argument("--mapping", choices=["ranked", "random", "inverse"], default="ranked")
    ap.add_argument("--ticks", type=int, default=50_000)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true", help="sim: print the structures and the plan only")
    args = ap.parse_args()

    scenarios = load_scenarios()
    cache = DiskCache(cache_dir())
    out_dir = data_dir() / "netlogo_llm"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.step == "llm":
        t0 = time.time()
        got = collect(scenarios, args.connector, cache, ask=True)
        report = [structure_report(s, est, f"{name}: {s.id}") for (name, _), (s, est) in got.items()]
        for (name, sid), (s, est) in got.items():
            try:
                exp = StructureExport.from_estimate(est, s, threshold=0.5, on_missing="error", name=f"{name} | {sid}")
                exp.save(structures_dir() / "roles" / f"{slug(sid + '__' + name)}.json")
            except agg.UndeterminedCellsError as exc:
                print(f"  {name} {sid}: structure not exported ({exc})")
        (out_dir / f"structures__{slug('-'.join(args.connector))}.md").write_text("\n".join(report), encoding="utf-8")
        print("\n".join(report))
        print(f"done in {time.time() - t0:.0f} s; structures in {structures_dir() / 'roles'}")
        return

    # ---------------------------------------------------------------- sim
    got = collect(scenarios, args.connector, cache, ask=False)
    any_s = scenarios[VARIANTS[0]]
    assignment_block = dict(any_s.assignment or {})
    exports = {}
    for (name, sid), (s, est) in got.items():
        exports[f"{name.split('/')[-1]}: {sid.replace('university_roles_', '')}"] = StructureExport.from_estimate(
            est, s, threshold=0.5, on_missing="error", name=f"{name} | {sid}")
    template = next(iter(exports.values()))
    refs = reference_matrices(*any_s.shape)

    def as_export(binary, label):
        return replace(template, binary=np.asarray(binary, bool), probability=np.asarray(binary, float),
                       valid_n=np.zeros(binary.shape, int), name=label, scenario_id=f"rule_based_{label}")

    assignment = RoleAssignment.for_export(template, **{**assignment_block, "ability_mapping": args.mapping})
    base = NetLogoParameters(stop_at=args.ticks).with_structures(Structure.ORGANIZED_ANARCHY)
    conditions = [
        cp.NetLogoCondition("rule: organized anarchy", base),
        cp.NetLogoCondition("rule: competent hierarchy", replace(base, decision_structure=Structure.COMPETENT_HIERARCHY)),
        cp.NetLogoCondition("rule: incompetent hierarchy", replace(base, decision_structure=Structure.INCOMPETENT_HIERARCHY)),
        cp.NetLogoCondition("target: hierarchical 6x5", base, export=as_export(refs["hierarchical"], "hierarchical_6x5"), assignment=assignment),
        cp.NetLogoCondition("target: specialized 6x5", base, export=as_export(refs["specialized"], "specialized_6x5"), assignment=assignment),
    ] + [cp.NetLogoCondition(label, base, export=exp, assignment=assignment) for label, exp in exports.items()]

    print(f"{len(conditions)} conditions x {args.seeds} seeds x {args.ticks} ticks = {len(conditions) * args.seeds} runs; "
          f"roles onto abilities: {args.mapping}; agents per role {assignment.role_counts(100)}, opportunities per type {assignment.type_counts(100)}")
    for c in conditions:
        print("  ", c.name)
    if args.dry_run:
        for (name, sid), (s, est) in got.items():
            print(structure_report(s, est, f"{name}: {sid}"))
        return

    t0 = time.time()
    runs = cp.run_netlogo_conditions(conditions, seeds=range(args.seeds), ticks=args.ticks, workers=args.workers)
    tag = f"{args.mapping}_{args.ticks}t_{args.seeds}s"
    runs.to_csv(out_dir / f"runs_{tag}.csv", index=False)
    print(f"{len(runs)} runs in {(time.time() - t0) / 60:.1f} min")

    styles = cp.style_table(runs, cp.NETLOGO_STYLES)
    styles.to_csv(out_dir / f"styles_{tag}.csv")
    chi_all = cp.style_chi_square(runs, cp.NETLOGO_STYLES)
    baseline = "rule: organized anarchy"
    target_of = {"strong_power": "target: hierarchical 6x5", "moderate_power": "target: specialized 6x5",
                 "weak_power": baseline}
    tests = []
    for label in exports:
        for ref in {baseline, target_of[label.split(": ")[1]]}:
            chi = cp.style_chi_square(runs, cp.NETLOGO_STYLES, conditions=[ref, label])
            cmpm = cp.compare_metrics(runs[runs.condition.isin([ref, label])], METRICS, ref, paired_on="seed")
            cmpm = cmpm[cmpm.condition == label].assign(reference=ref, chi2=chi.chi2, chi2_p=chi.p_value, cramers_v=chi.cramers_v)
            tests.append(cmpm)
    for rule in ("rule: competent hierarchy", "rule: incompetent hierarchy", "target: hierarchical 6x5", "target: specialized 6x5"):
        cmpm = cp.compare_metrics(runs[runs.condition.isin([baseline, rule])], METRICS, baseline, paired_on="seed")
        tests.append(cmpm[cmpm.condition == rule].assign(reference=baseline))
    tests = pd.concat(tests, ignore_index=True)
    p = tests["p_value"].to_numpy(dtype=float)
    finite = np.isfinite(p)
    order = np.argsort(np.where(finite, p, np.inf))
    adj, running, m = np.full(len(p), np.nan), 0.0, int(finite.sum())
    for rank, i in enumerate(order[:m]):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    tests["p_holm"] = adj
    tests.to_csv(out_dir / f"tests_{tag}.csv", index=False)

    summary = runs.groupby("condition", sort=False)[METRICS].mean()
    lines = [f"# NetLogo transfer check ({tag})", "",
             f"{len(conditions)} conditions, seeds 0 to {args.seeds - 1}, {args.ticks} ticks, flights on, availability and access unrestricted, roles onto abilities: {args.mapping}.", "",
             f"Chi-square over all conditions (resolutions vs. oversights): chi2 = {chi_all.chi2:.1f}, df = {chi_all.dof}, p = {chi_all.p_value:.3g}, V = {chi_all.cramers_v:.3f}", "",
             "## Means per condition", "", summary.round(3).to_markdown(), "",
             "## Styles (pooled)", "", styles.round(3).to_markdown(), "",
             "## Tests (paired by seed; Wilcoxon; Holm over all rows)", "",
             tests[["condition", "reference", "metric", "mean", "baseline_mean", "difference", "diff_ci_low", "diff_ci_high", "p_value", "p_holm"]].round(4).to_markdown(index=False), ""]
    for (name, sid), (s, est) in got.items():
        lines.append(structure_report(s, est, f"{name}: {sid}"))
    (out_dir / f"report_{tag}.md").write_text("\n".join(lines), encoding="utf-8")
    print(summary[["share_resolutions", "decisions", "flights", "resolution_share_L1", "resolution_share_L2"]].round(3).to_string())
    print(f"report: {out_dir / f'report_{tag}.md'}")


if __name__ == "__main__":
    main()
