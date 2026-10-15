# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo>=0.24.2",
# ]
# ///
import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full", app_title="Garbage Can Model")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import altair as alt
    import pandas as pd

    from gcm.common import StructureKind
    from gcm.fortran import (
        FortranComponents,
        FortranParameters,
        GarbageCanFortran,
        Load,
        MovementCondition,
        format_histories,
        summarise,
    )
    from gcm.fortran import (
        experiments as fx,
    )
    from gcm.fortran.data import ENTRY_CONDITIONS
    from gcm.netlogo import (
        GarbageCanABM,
        NetLogoComponents,
        NetLogoParameters,
        Structure,
    )
    from gcm.netlogo import experiments as nx
    from gcm.netlogo.hierarchy import hierarchy_levels

    pd.set_option("display.width", 200)
    return (
        ENTRY_CONDITIONS,
        FortranComponents,
        FortranParameters,
        GarbageCanABM,
        GarbageCanFortran,
        Load,
        MovementCondition,
        NetLogoComponents,
        NetLogoParameters,
        Structure,
        StructureKind,
        alt,
        format_histories,
        fx,
        hierarchy_levels,
        nx,
        pd,
        summarise,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # The Garbage Can Model of Organizational Choice

    Two faithful Python re-implementations of the Garbage Can Model (GCM), built as the
    rule-based baseline for the thesis *Simulation ausgewählter Bestandteile des
    Entscheidungsprozesses im Garbage-Can-Modell mit generativen KI-/LLM-Agenten*:

    1. **The original FORTRAN simulation** of Cohen, March and Olsen (1972), ported from the
       listing in the appendix of the paper (package `gcm.fortran`).
    2. **The agent-based reconstruction** of Fioretti and Lomi (2008, 2010), ported from Guido
       Fioretti's current NetLogo source `GarbageCan_simplified17.nlogox` (package
       `gcm.netlogo`).

    Both ports factor every behavioural assumption into a small, swappable component
    (a Python `Protocol`). Section 3 documents the seams. Section 5 uses one of them: it
    replaces the decision structure by a contextual one that language models derive from a
    natural-language description of the organization, and compares the resulting simulations
    with the rule-based baselines.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. The FORTRAN model (Cohen, March and Olsen 1972)

    Four streams meet in an organization: **choices** (garbage cans), **problems**,
    **solutions** (a single coefficient that deflates energy) and **decision makers**
    (energy). Each period every active problem attaches to the accessible choice that is
    *closest to decision* and every decision maker spends the period's energy on the eligible
    choice that is closest to decision. A choice is made once the cumulative effective energy
    spent on it equals or exceeds the summed requirements of the problems attached to it.
    A choice is made **by resolution** if problems are attached at that moment (they are
    solved), **by oversight** if no problem ever attached to it, and **by flight** if problems
    had been attached earlier but left before the choice was made.

    The organization is described by four dimensions with three pure settings each
    (81 variants), studied under four combinations of entry orders (324 situations):
    net energy **load** (light / moderate / heavy), **access structure** (problems to choices),
    **decision structure** (decision makers to choices) and **energy distribution**.
    """)
    return


@app.cell
def _(ENTRY_CONDITIONS, MovementCondition, mo):
    f_entry = mo.ui.dropdown(options=list(ENTRY_CONDITIONS), value="choices_a/problems_a", label="entry times")
    f_load = mo.ui.dropdown(options=["light", "moderate", "heavy"], value="light", label="net energy load")
    f_access = mo.ui.dropdown(options=["unsegmented", "hierarchical", "specialized"], value="hierarchical", label="access structure")
    f_decision = mo.ui.dropdown(options=["unsegmented", "hierarchical", "specialized"], value="hierarchical", label="decision structure")
    f_energy = mo.ui.dropdown(
        options={"important people less energy (E0)": 0, "equal energy (E1)": 1, "important people more energy (E2)": 2},
        value="equal energy (E1)",
        label="energy distribution",
    )
    f_arith = mo.ui.dropdown(
        options=["exact", "float64", "ibm360", "ibm360-nearest"], value="exact", label="arithmetic backend"
    )
    f_movement = mo.ui.dropdown(
        options={m.name: m for m in MovementCondition},
        value="BOTH_MOVE",
        label="movement condition (NA)",
    )
    mo.vstack(
        [
            mo.md("### 1.1 One organizational situation"),
            mo.hstack([f_entry, f_load, f_access, f_decision], wrap=True),
            mo.hstack([f_energy, f_arith, f_movement], wrap=True),
        ]
    )
    return f_access, f_arith, f_decision, f_energy, f_entry, f_load, f_movement


@app.cell
def _(
    FortranComponents,
    FortranParameters,
    GarbageCanFortran,
    Load,
    StructureKind,
    f_access,
    f_arith,
    f_decision,
    f_energy,
    f_entry,
    f_load,
    f_movement,
    summarise,
):
    f_params = FortranParameters.from_entry_condition(
        f_entry.value, arithmetic=f_arith.value, movement=f_movement.value
    )
    f_components = FortranComponents.classic(
        access=StructureKind(f_access.value),
        decision=StructureKind(f_decision.value),
        energy=f_energy.value,
        params=f_params,
    )
    f_model = GarbageCanFortran(f_params, Load[f_load.value.upper()], f_components)
    f_history = f_model.run()
    f_stats = summarise(f_history, f_model.energy_reserve, f_model.energy_wastage, f_model.state.dm_resting_periods)
    return f_history, f_stats


@app.cell
def _(f_history, f_stats, mo, pd):
    _styles = pd.DataFrame(
        [
            {
                "choice": o.choice + 1,
                "entered": None,
                "made in period": o.period_made,
                "style": o.style.value if o.style else "not made",
                "problems solved": ", ".join(str(j + 1) for j in o.problems_solved),
            }
            for o in f_history.outcomes
        ]
    ).drop(columns=["entered"])
    _summary = pd.DataFrame(
        {
            "statistic": [
                "choices made (of 10)",
                "by resolution",
                "by oversight",
                "by flight",
                "problems not solved (KW)",
                "problem activity / persistence (KT)",
                "problem latency (KU)",
                "problem velocity (KV)",
                "decision maker velocity (KX)",
                "decision maker inactivity (KS)",
                "choice persistence / decision time (KY)",
                "choices not made (KZ)",
                "energy reserve (XR)",
                "energy wastage (XS)",
            ],
            "value": [
                f_stats.choices_made,
                f_stats.by_resolution,
                f_stats.by_oversight,
                f_stats.by_flight,
                f_stats.problems_not_solved,
                f_stats.problem_persistence,
                f_stats.problem_latency,
                f_stats.problem_velocity,
                f_stats.dm_velocity,
                f_stats.dm_inactivity,
                f_stats.choice_persistence,
                f_stats.choices_not_made,
                round(f_stats.energy_reserve, 3),
                round(f_stats.energy_wastage, 3),
            ],
        }
    )
    mo.hstack(
        [
            mo.vstack([mo.md("**Decision style per choice**"), mo.ui.table(_styles, selection=None, page_size=10)]),
            mo.vstack([mo.md("**The ten summary statistics of the program**"), mo.ui.table(_summary, selection=None, page_size=14)]),
        ],
        widths=[1, 1],
        wrap=True,
    )
    return


@app.cell
def _(f_history, format_histories, mo):
    mo.accordion(
        {
            "Histories as printed by the program under IO = 2 (choice activation, decision maker activity, problem history)": mo.ui.code_editor(
                format_histories(f_history), language="text", disabled=True
            )
        }
    )
    return


@app.cell
def _(alt, f_history, mo, pd):
    _rows = []
    for _t in range(f_history.requirement.shape[0]):
        for _i in range(f_history.requirement.shape[1]):
            if f_history.choices[_t, _i] == 0:
                continue
            _rows.append({"period": _t + 1, "choice": f"choice {_i + 1}", "energy required (XERC)": f_history.requirement[_t, _i],
                          "energy expended (XEE)": f_history.energy[_t, _i], "status": ["inactive", "active", "made"][f_history.choices[_t, _i]]})
    _df = pd.DataFrame(_rows).melt(id_vars=["period", "choice", "status"], var_name="quantity", value_name="energy")
    _chart = (
        alt.Chart(_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("period:Q", scale=alt.Scale(domain=[1, 20])),
            y="energy:Q",
            color=alt.Color("quantity:N", legend=alt.Legend(orient="top", title=None)),
            strokeDash=alt.StrokeDash("quantity:N", legend=None),
            tooltip=["period", "choice", "quantity", alt.Tooltip("energy:Q", format=".2f"), "status"],
        )
        .properties(width=150, height=110)
        .facet(facet=alt.Facet("choice:N", title=None), columns=5)
        .resolve_scale(y="independent")
    )
    mo.vstack([mo.md("**Energy required vs. cumulative effective energy expended per choice.** A choice is made in the first period in which the expended energy reaches the requirement; ghost energy (energy left on a choice after its problems have moved on) is what makes decisions by flight and oversight cheap."), _chart])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 1.2 Docking against the published results

    Running all 324 situations takes about a second. The tables below are computed with the
    default *exact* arithmetic backend, which implements the paper's stated semantics
    ("equals or exceeds") by comparing energies after rounding to nine decimals. This matters:
    the parameter space is full of exact ties (three light-load problems need 3 × 1.1 = 3.3,
    ten equal decision makers deliver 10 × 0.6 × 0.55 = 3.3 in one period), and in 1972 those
    ties were decided by the truncating hexadecimal arithmetic of an IBM System/360. Pick
    `ibm360` above to see an emulation of that arithmetic; it flips some rows of Table 5 the
    published way and others the wrong way, which is the expected signature of a machine
    dependence that cannot be recovered from the listing alone.
    """)
    return


@app.cell
def _(f_arith, fx):
    f_all = fx.run_all(arithmetic=f_arith.value)
    return (f_all,)


@app.cell
def _(f_all, fx, mo):
    _t1 = fx.table_1(f_all)
    _t2 = fx.table_2(f_all)
    _codes = ["0200", "1110", "0111", "1112", "2112", "1111", "0002", "1002", "0001", "1221", "2211", "1211"]
    _t5 = fx.table_5_rows(f_all, _codes).loc[_codes]
    _t5_pub = {
        "0200": (0.68, 0, 154, 100, 0), "1110": (0.21, 210, 23, 58, 34), "0111": (0.65, 57, 60, 66, 14),
        "1112": (0.38, 210, 25, 66, 31), "2112": (0.24, 248, 32, 55, 38), "1111": (0.31, 200, 30, 58, 28),
        "0002": (1.0, 0, 0, 100, 0), "1002": (0, 310, 0, 90, 20), "0001": (1.0, 0, 0, 100, 0),
        "1221": (0.54, 158, 127, 15, 83), "2211": (0.61, 101, 148, 73, 52), "1211": (0.62, 78, 151, 76, 39),
    }
    import pandas as _pd

    _t5p = _pd.DataFrame(_t5_pub, index=_t5.columns).T
    _t5c = _pd.concat({"this port": _t5, "published": _t5p}, axis=1)
    mo.vstack(
        [
            mo.md(
                f"**Table 1.** Proportion of choices that resolve problems, by load and access structure "
                f"(left: this port, right: Cohen, March and Olsen 1972). Mean choices not made: "
                f"{f_all['choices_not_made'].mean():.2f} (paper 1.0); mean problems not solved: "
                f"{f_all['problems_not_solved'].mean():.2f} (paper 12.3)."
            ),
            mo.hstack([_t1, fx.TABLE_1_PUBLISHED], wrap=True),
            mo.md("**Table 2.** Effects of variations in load (left: this port, right: published)."),
            mo.hstack([_t2, fx.TABLE_2_PUBLISHED], wrap=True),
            mo.md(
                "**Table 5 rows** (organizational codes *load access decision energy*, averaged over the four entry conditions): "
                "proportion resolution, problem activity, problem latency, decision maker activity, decision time."
            ),
            _t5c,
        ]
    )
    return


@app.cell
def _(alt, f_all, mo):
    _chart = (
        alt.Chart(f_all)
        .transform_fold(["by_resolution", "by_oversight", "by_flight"], as_=["style", "count"])
        .mark_bar()
        .encode(
            x=alt.X("load:N", sort=["light", "moderate", "heavy"], title=None),
            y=alt.Y("sum(count):Q", stack="normalize", title="share of choices made"),
            color=alt.Color("style:N", sort=["by_resolution", "by_flight", "by_oversight"]),
            column=alt.Column("access:N", sort=["unsegmented", "hierarchical", "specialized"], title="access structure"),
            tooltip=["style:N", "sum(count):Q"],
        )
        .properties(width=130, height=180)
    )
    mo.vstack([mo.md("**Decision styles across all 324 situations.** Property 1 of the paper: resolution is not the most common style except where flight is restricted (specialized access) or under light load."), _chart])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. The agent-based model (Fioretti and Lomi; NetLogo port)

    The organization is a 50 × 50 torus. Participants, opportunities, solutions and problems
    random-walk one patch per tick. Where at least one participant, one opportunity and one
    solution meet, a decision is made: **by oversight** if no problem is there, **by
    resolution** if the summed ability of the participants times the efficiency of the best
    solution covers the summed difficulty of the problems, otherwise the process is
    **blocked** and everybody on the patch stays put. A blocked process can be freed by
    **flights**: an opportunity that walks in takes the most difficult problem away
    (*postponement*), a participant that walks in takes it along (*buck-passing*).

    Organizational structure is imposed through movement constraints. Opportunities are
    ranked by importance in a pyramid with a chosen span of control; in a *competent
    hierarchy* only able participants (efficient solutions, difficult problems) may meet
    important opportunities, in an *incompetent hierarchy* the reverse holds.
    """)
    return


@app.cell
def _(Structure, mo):
    n_participants = mo.ui.slider(10, 500, 10, value=100, label="participants")
    n_opportunities = mo.ui.slider(10, 500, 10, value=100, label="opportunities")
    n_solutions = mo.ui.slider(10, 500, 10, value=100, label="solutions")
    n_problems = mo.ui.slider(10, 500, 10, value=100, label="problems")
    ability = mo.ui.range_slider(0, 10, 1, value=[0, 10], label="ability range")
    efficiency = mo.ui.range_slider(0, 1, 0.1, value=[0, 1], label="efficiency range")
    difficulty = mo.ui.range_slider(0, 10, 1, value=[0, 10], label="difficulty range")
    span = mo.ui.slider(1, 10, 1, value=2, label="span of control")
    _opts = [s.value for s in Structure]
    decision_structure = mo.ui.dropdown(_opts, value="competent hierarchy", label="decision structure")
    availability_structure = mo.ui.dropdown(_opts, value="competent hierarchy", label="availability structure")
    access_structure = mo.ui.dropdown(_opts, value="competent hierarchy", label="access structure")
    postpone = mo.ui.switch(value=True, label="postpone?")
    buckpass = mo.ui.switch(value=True, label="buckpass?")
    ticks = mo.ui.slider(100, 50_000, 100, value=2000, label="ticks (BehaviorSpace: 50 000)")
    seed = mo.ui.number(0, 10_000, value=1, label="seed")
    run_abm = mo.ui.run_button(label="Run the agent-based model")
    mo.vstack(
        [
            mo.md("### 2.1 One run"),
            mo.hstack([n_participants, n_opportunities, n_solutions, n_problems], wrap=True),
            mo.hstack([ability, efficiency, difficulty, span], wrap=True),
            mo.hstack([decision_structure, availability_structure, access_structure], wrap=True),
            mo.hstack([postpone, buckpass, ticks, seed, run_abm], wrap=True),
        ]
    )
    return (
        ability,
        access_structure,
        availability_structure,
        buckpass,
        decision_structure,
        difficulty,
        efficiency,
        n_opportunities,
        n_participants,
        n_problems,
        n_solutions,
        postpone,
        run_abm,
        seed,
        span,
        ticks,
    )


@app.cell
def _(
    GarbageCanABM,
    NetLogoParameters,
    Structure,
    ability,
    access_structure,
    availability_structure,
    buckpass,
    decision_structure,
    difficulty,
    efficiency,
    mo,
    n_opportunities,
    n_participants,
    n_problems,
    n_solutions,
    postpone,
    run_abm,
    seed,
    span,
    ticks,
):
    mo.stop(not run_abm.value, mo.md("*Press the button to run. 2 000 ticks take a few seconds; a full 50 000-tick BehaviorSpace run about a minute.*"))
    abm_params = NetLogoParameters(
        number_of_participants=n_participants.value,
        number_of_opportunities=n_opportunities.value,
        number_of_solutions=n_solutions.value,
        number_of_problems=n_problems.value,
        min_ability=ability.value[0],
        max_ability=ability.value[1],
        min_efficiency=efficiency.value[0],
        max_efficiency=efficiency.value[1],
        min_difficulty=difficulty.value[0],
        max_difficulty=difficulty.value[1],
        span_of_control=span.value,
        decision_structure=Structure(decision_structure.value),
        availability_structure=Structure(availability_structure.value),
        access_structure=Structure(access_structure.value),
        postpone=postpone.value,
        buckpass=buckpass.value,
        stop_at=ticks.value,
        seed=int(seed.value),
    )
    abm = GarbageCanABM(abm_params, record_every=max(1, ticks.value // 100))
    abm_results = abm.run()
    return abm, abm_params, abm_results


@app.cell
def _(abm, abm_params, abm_results, hierarchy_levels, mo, pd):
    _r = abm_results
    _rows = [
        ("Total Resolutions", _r.num_resolutions),
        ("Total Oversights", _r.num_oversights),
        ("share of decisions by resolution", round(_r.share_resolutions, 4)),
        ("Resolutions High / Low Levels", f"{_r.num_resolutions_high} / {_r.num_resolutions_low}" if abm.hierarchy_active else "N/A"),
        ("Oversights High / Low Levels", f"{_r.num_oversights_high} / {_r.num_oversights_low}" if abm.hierarchy_active else "N/A"),
        ("blocked processes followed by resolution / oversight", f"{_r.num_blocked_resolutions} / {_r.num_blocked_oversights}"),
        ("Currently Blocked Decisions", _r.currently_blocked),
        ("Ave Duration Blocked", round(_r.ave_duration_blocked, 2)),
        ("Total Postponements", _r.num_postponements),
        ("Currently Postponed Problems", _r.currently_postponed),
        ("Ave Duration Postponed", round(_r.ave_duration_postponed, 2)),
        ("Total Buck-Passings", _r.num_buck_passings),
        ("Currently Buck-Passed Problems", _r.currently_passed),
        ("Ave Duration Buck-Passed", round(_r.ave_duration_passed, 2)),
    ]
    _hier = (
        f"Hierarchy: {hierarchy_levels(abm_params.number_of_opportunities, abm_params.span_of_control)} levels, "
        f"hierarchy divide {abm.hierarchy_divide} (opportunities with who ≤ {abm.hierarchy_divide} are high-importance)."
        if abm.hierarchy_active
        else "Organized anarchy in all three structures: no hierarchy."
    )
    mo.vstack(
        [
            mo.md(f"**Monitors after {_r.ticks} ticks.** {_hier}"),
            mo.ui.table(pd.DataFrame(_rows, columns=["monitor", "value"]), selection=None, page_size=14),
        ]
    )
    return


@app.cell
def _(abm, alt, mo, pd):
    _s = abm.snapshot()
    _pts = pd.concat(
        [
            pd.DataFrame(_s["opportunities"], columns=["x", "y", "value", "blocked", "flying"]).assign(breed="opportunity"),
            pd.DataFrame(_s["participants"], columns=["x", "y", "value", "blocked", "flying"]).assign(breed="participant"),
            pd.DataFrame(_s["solutions"], columns=["x", "y", "value", "blocked"]).assign(breed="solution", flying=False),
            pd.DataFrame(_s["problems"], columns=["x", "y", "value", "blocked", "flying"]).assign(breed="problem"),
        ]
    )
    _patches = pd.DataFrame(
        [{"x": i % _s["width"], "y": i // _s["width"], "colour": c} for i, c in _s["colors"].items()]
    )
    _bg = (
        alt.Chart(_patches)
        .mark_rect(opacity=0.9)
        .encode(
            x=alt.X("x:O", axis=None), y=alt.Y("y:O", axis=None, sort="descending"),
            color=alt.Color("colour:N", scale=alt.Scale(domain=["white", "lime", "sky", "brown"], range=["#f2f2f2", "#7bd88f", "#8ecae6", "#b08968"]), legend=alt.Legend(title="patch")),
            tooltip=["x", "y", "colour"],
        )
        if len(_patches)
        else alt.Chart(pd.DataFrame({"x": [], "y": []})).mark_rect()
    )
    _fg = (
        alt.Chart(_pts)
        .mark_point(filled=True, size=42)
        .encode(
            x=alt.X("x:O", axis=None, scale=alt.Scale(domain=list(range(_s["width"])))),
            y=alt.Y("y:O", axis=None, sort="descending", scale=alt.Scale(domain=list(range(_s["height"])))),
            shape=alt.Shape("breed:N", scale=alt.Scale(domain=["opportunity", "participant", "solution", "problem"], range=["square", "circle", "diamond", "triangle-up"])),
            color=alt.Color("breed:N", scale=alt.Scale(domain=["opportunity", "participant", "solution", "problem"], range=["#f4a261", "#e9c46a", "#e63946", "#6a4c93"])),
            opacity=alt.condition(alt.datum.blocked, alt.value(1.0), alt.value(0.7)),
            tooltip=["breed", "x", "y", alt.Tooltip("value:Q", format=".2f"), "blocked", "flying"],
        )
    )
    mo.vstack(
        [
            mo.md("**The world at the end of the run.** White patches host blocked decision processes (blocked agents drawn opaque), brown patches a flying pair, lime and sky-blue the resolutions and oversights of the last tick."),
            (_bg + _fg).resolve_scale(color="independent", shape="independent").properties(width=520, height=520).configure_view(stroke="#888"),
        ]
    )
    return


@app.cell
def _(abm, alt, mo, pd):
    _tl = pd.DataFrame(abm.timeline)
    _ev = pd.DataFrame([e.__dict__ for e in abm.events])
    _cum = (
        alt.Chart(_tl.melt(id_vars=["ticks"], value_vars=["num_resolutions", "num_oversights", "num_postponements", "num_buck_passings"], var_name="counter", value_name="count"))
        .mark_line()
        .encode(x="ticks:Q", y="count:Q", color="counter:N", tooltip=["ticks", "counter", "count"])
        .properties(width=330, height=220, title="cumulative counters")
    )
    _share = (
        alt.Chart(_tl)
        .mark_line(color="#2a9d8f")
        .encode(x="ticks:Q", y=alt.Y("share_resolutions:Q", title="resolutions / decisions"), tooltip=["ticks", alt.Tooltip("share_resolutions:Q", format=".3f")])
        .properties(width=330, height=220, title="share of decisions by resolution")
    )
    _by_imp = (
        alt.Chart(_ev[_ev.kind.isin(["resolution", "oversight"])].assign(important=lambda d: d.opportunity <= abm.hierarchy_divide))
        .mark_bar()
        .encode(x=alt.X("kind:N", title=None), y=alt.Y("count():Q", title="decisions"), color=alt.Color("important:N", title="high-importance opportunity"), tooltip=["kind", "important", "count()"])
        .properties(width=200, height=220, title="decisions by importance")
        if abm.hierarchy_active and len(_ev)
        else mo.md("")
    )
    mo.vstack([mo.hstack([_cum, _share], wrap=True), _by_imp, mo.md(f"**Event log** ({len(_ev)} decisions and flights; the information `show-details?` prints in NetLogo)."), mo.ui.table(_ev, page_size=8, selection=None) if len(_ev) else mo.md("no events")])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 2.2 The BehaviorSpace experiments

    The `.nlogox` file defines twelve experiments: three structures (organized anarchy,
    competent hierarchy, incompetent hierarchy applied to all three choosers) times four flight
    settings (none, postponement, buck-passing, both), each with 100 agents per breed for
    50 000 ticks and 1 000 repetitions. The command `uv run gcm-netlogo --ticks 50000
    --repetitions 30 --workers 8 --out results.csv` runs them in full; here a short version
    can be launched interactively. The four properties Fioretti highlights are that most
    decisions are made by oversight, that flights raise the proportion of resolutions, that
    organized anarchies out-resolve hierarchies, and that incompetent hierarchies are at
    least as efficient as competent ones.
    """)
    return


@app.cell
def _(mo):
    bs_ticks = mo.ui.slider(500, 20_000, 500, value=2000, label="ticks per run")
    bs_reps = mo.ui.slider(1, 10, 1, value=2, label="repetitions (seeds)")
    bs_workers = mo.ui.slider(1, 16, 1, value=2, label="worker processes")
    run_bs = mo.ui.run_button(label="Run the 12 experiments")
    mo.hstack([bs_ticks, bs_reps, bs_workers, run_bs], wrap=True)
    return bs_reps, bs_ticks, bs_workers, run_bs


@app.cell
def _(alt, bs_reps, bs_ticks, bs_workers, mo, nx, run_bs):
    mo.stop(not run_bs.value, mo.md("*Press the button to run the experiments (about 1.4 ms per tick and run).*"))
    bs_results = nx.run_experiments(repetitions=bs_reps.value, ticks=bs_ticks.value, workers=bs_workers.value)
    _summary = nx.summarise_experiments(bs_results)
    _chart = (
        alt.Chart(bs_results)
        .mark_bar()
        .encode(
            x=alt.X("experiment:N", sort=list(_summary.index), title=None),
            y=alt.Y("mean(share_resolutions):Q", title="resolutions / decisions"),
            color=alt.Color("decision_structure:N", title="structure"),
            tooltip=["experiment", alt.Tooltip("mean(share_resolutions):Q", format=".3f"), "mean(num_resolutions):Q", "mean(num_oversights):Q"],
        )
        .properties(width=560, height=260)
    )
    mo.vstack([_chart, _summary])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Architecture: where the LLM agents will plug in

    Both packages separate the *simulation core* (streams, meetings, energy accounting,
    histories) from the *behavioural assumptions*, each of which is a `Protocol` with a
    rule-based default. The thesis substitutes the decision and access structures (research
    question 1) and optionally the energy allocation; the other seams are there so that the
    remaining assumptions can be varied in the same way. The table lists the exact methods a
    substitute has to provide; section 5 provides one for the decision structure.

    | Aspect of the GCM | FORTRAN model (`gcm.fortran.interfaces`) | NetLogo model (`gcm.netlogo.interfaces`) |
    |---|---|---|
    | Decision structure (which participants may use which opportunities) | `DecisionStructure.matrix(state)` returns the boolean matrix D, queried **every period** | `DecisionStructure.participant_may_enter(...)`, `.opportunity_may_enter(...)` |
    | Access structure (which problems reach which opportunities) | `AccessStructure.matrix(state)` returns A | `AccessStructure.problem_may_enter(...)`, `.opportunity_may_enter(...)` |
    | Availability structure (solutions) | not part of the original model (single solution coefficient) | `AvailabilityStructure.solution_may_enter(...)`, `.opportunity_may_enter(...)` |
    | Energy allocation of decision makers (optional substitution) | `DecisionMakerAllocationRule.choose(dm, state)` | movement is a random walk; a substitute would replace the direction choice (not exposed as a seam yet, see below) |
    | Problem allocation | `ProblemAllocationRule.choose(problem, state)` | random walk |
    | Energy distribution | `EnergyDistribution.matrix(n_dm, n_periods, arith)` | ability drawn uniformly at setup |
    | Decision rule | `ChoiceRule.is_made(choice, state)` | `ResolutionRule.resolves(here, model)` |
    | Flights | emergent (problems leave for a better choice) | `FlightSelector.postponement(...)`, `.buck_passing(...)` |

    A substitute is a plain object with the listed methods and a `name`; it is handed to the
    model through `FortranComponents` / `NetLogoComponents`. Because the structure components
    are consulted on every allocation (FORTRAN) or every attempted move (NetLogo), an
    LLM-backed implementation should decide at a coarser granularity (for instance once per
    participant per period, or once per participant and opportunity level) and cache, which
    also keeps the number of API calls small and independent, as the Exposé requires.

    The cell below shows the seam in action with a *rule-based* stand-in: a decision structure
    in which every participant is admitted to opportunities of its own hierarchy level only
    (the "specialized" arrangement of the 1972 paper, transplanted into the NetLogo model).
    """)
    return


@app.cell
def _(GarbageCanABM, NetLogoComponents, NetLogoParameters, Structure, mo):
    from gcm.netlogo.hierarchy import level_of as _level_of

    class LevelSpecializedDecisionStructure:
        """Participants are assigned to a pyramid level by ability rank; they may only meet
        opportunities of that level. Illustrates the shape of a substitute component."""

        name = "level-specialized (demo)"

        def __init__(self, model):
            ranked = sorted(model.participants, key=lambda a: -a.ability)
            self._level = {}
            for rank, a in enumerate(ranked):
                self._level[a.who] = _level_of(rank * model.params.number_of_opportunities // len(ranked), model.params.span_of_control)

        def _opp_level(self, o, model):
            return _level_of(o.who, model.params.span_of_control)

        def participant_may_enter(self, participant, target, model):
            lvl = self._level[participant.who]
            return all(self._opp_level(o, model) == lvl for o in target.opportunities)

        def opportunity_may_enter(self, opportunity, target, model):
            lvl = self._opp_level(opportunity, model)
            return all(self._level[a.who] == lvl for a in target.participants)

    _p = NetLogoParameters(seed=1, stop_at=1500).with_structures(Structure.ORGANIZED_ANARCHY)
    _demo = GarbageCanABM(_p, record_events=False)
    _comps = NetLogoComponents.classic(_p)
    _comps.decision_structure = LevelSpecializedDecisionStructure(_demo)
    _custom = GarbageCanABM(_p, components=_comps, record_events=False)
    _r_base = _demo.run()
    _r_custom = _custom.run()
    mo.md(
        f"""
        Same seed and parameters, 1 500 ticks. Organized anarchy: **{_r_base.num_resolutions}** resolutions and
        **{_r_base.num_oversights}** oversights (share {_r_base.share_resolutions:.3f}). With the level-specialized
        decision structure plugged in: **{_r_custom.num_resolutions}** resolutions and **{_r_custom.num_oversights}**
        oversights (share {_r_custom.share_resolutions:.3f}). The simulation core did not change; only the
        component answering "may this participant step next to that opportunity?" did.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Notes on fidelity

    * **FORTRAN.** The listing in the appendix is reproduced block by block (labels are cited in
      the source). Entry-time cards match the orders printed in the paper. The program does not
      compute decision styles itself; they are derived from the histories following the
      definitions on p. 8 (resolution if problems are attached when the choice is made, flight
      if problems had been attached earlier, oversight otherwise). Two details are not
      recoverable from the listing: the initial value of a choice's requirement (`XERC(I) = 1.1`
      is the reading adopted; alternatives are exposed as a parameter) and the tie-breaking of
      the 1972 machine (see 1.2). The summary statistics accumulate from period 2 onwards, as the
      program does.
    * **NetLogo.** Patch colours and `pcolor-white-since` are model state and are treated as
      such. The `ask patches [ask <breed>-here …]` idiom that lets flying pairs move about
      e − 1 patches per tick is emulated exactly (random patch order with re-queuing). Ties in
      `max-one-of` and `one-of` are broken at random. The thresholds `(max − min) / 2` and the
      `who <= hierarchy-divide` comparison are kept literally. The `who` numbering follows the
      code (lower `who` = more important), not the contradicting comment in `setup`.
    * **Verification.** `uv run pytest` runs 30 tests: matrices against the printed arrays,
      Table 5 rows that the port reproduces exactly, docking tolerances for Tables 1 and 2,
      hand-built patch situations for oversight, block, resolution and postponement, the
      flying-pair rate, and the four qualitative properties of the NetLogo model.
    """)
    return


@app.cell
def _():
    import numpy as np

    from gcm.contextual import aggregate as cx_agg
    from gcm.contextual import compare as cx_cp
    from gcm.contextual import prompts as cx_prompts
    from gcm.contextual.cache import DiskCache
    from gcm.contextual.connectors import MockConnector, available_connectors
    from gcm.contextual.experiment import ExperimentConfig, expand_grid, n_calls, plan_calls, run_experiment
    from gcm.contextual.netlogo_adapter import RoleAssignment
    from gcm.contextual.paths import cache_dir, runs_dir, structures_dir
    from gcm.contextual.references import reference_matrices
    from gcm.contextual.representation import REPRESENTATIONS, TEMPLATES, entity_sentence, render
    from gcm.contextual.scenario import load_scenarios
    from gcm.contextual.structure_io import StructureExport

    cx_scenarios = load_scenarios()
    return (
        DiskCache,
        ExperimentConfig,
        MockConnector,
        REPRESENTATIONS,
        RoleAssignment,
        StructureExport,
        TEMPLATES,
        available_connectors,
        cache_dir,
        cx_agg,
        cx_cp,
        cx_prompts,
        cx_scenarios,
        entity_sentence,
        expand_grid,
        n_calls,
        np,
        plan_calls,
        reference_matrices,
        render,
        run_experiment,
        runs_dir,
        structures_dir,
    )


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. A contextual decision structure

    ### 5.1 What is replaced, and why only this

    In the 1972 program the **decision structure** is a fixed 0/1 matrix D that relates decision
    makers to choice opportunities, and the **access structure** a fixed 0/1 matrix A that relates
    problems to choice opportunities (Cohen, March and Olsen 1972, pp. 6 and 7). Both are given as
    data; the hierarchy they express lives only in the index order (a low number is an important
    element), and who actually attends a choice emerges from the energy dynamics. The NetLogo model
    (Fioretti and Lomi 2008; Fioretti 2024) applies the same yes/no logic as a movement rule: under
    the three chooser settings a participant may or may not step next to an opportunity depending
    on whether its ability lies above a threshold and whether the opportunity counts as important
    (`who <= hierarchy-divide`).

    This section replaces exactly that component by a **contextual** one. "Contextual" means
    that the organization is described in natural language, that language models are asked, for
    every participant and every opportunity, whether the participant is *permitted* to take part,
    and that the repeated answers are aggregated into a probability matrix and a binary structure
    (research question 1). The language model judges **eligibility only**. It never decides whether
    a participant would want to attend, has time or would be useful; those are the behavioural
    assumptions of the models, and they stay rule-based, so that any change in the outcome
    distributions (research question 2) can be attributed to the structure alone.

    The structure returns into the simulations as a file. A new implementation of the existing
    `DecisionStructure` protocols loads it (`gcm.contextual.fortran_adapter`,
    `gcm.contextual.netlogo_adapter`), so the simulation never calls a language model and runs
    at the same speed as before. Scenarios are data files (`gcm/contextual/scenarios/*.yaml`); the
    three reference scenarios describe the pure structures of the paper in plain language and
    carry the known matrices, so they validate the pipeline. The university scenarios are
    placeholders. Prompts never mention the model, the theory or the names of the structures, so
    that answers come from the described context and not from memorized theory. Two words need
    keeping apart: in this text "organized anarchy" is the organization type of the 1972 paper,
    such as a university; in the NetLogo code the same words name the setting without
    restrictions. This section calls the unrestricted matrix *unsegmented*, as the paper does.

    The factors of the robustness audit follow the TRAILS taxonomy (Ye et al. 2026):
    representation format, prompt wording, perspective, item order, language, model, seed and
    temperature. Every raw answer is logged as JSON Lines, every request is cached on disk, and
    language models are only ever called when a run button is pressed.
    """)
    return


@app.cell
def _(REPRESENTATIONS, cx_scenarios, mo):
    cx_scenario = mo.ui.dropdown(
        options={f"{s.kind}: {s.id}": s.id for s in cx_scenarios.values()},
        value="reference: reference_hierarchical",
        label="scenario",
    )
    cx_repr = mo.ui.dropdown(options=list(REPRESENTATIONS), value="prose", label="representation")
    cx_lang = mo.ui.dropdown(options=["en", "de"], value="en", label="language")
    cx_importance = mo.ui.switch(value=False, label="show level and importance in the prompt")
    mo.vstack(
        [
            mo.md("### 5.2 Representations: how a scenario becomes text"),
            mo.md(
                "A scenario has ordered participants and opportunities (the order is the importance order and "
                "fixes the matrix indices), a description of the organization and statements about how it works. "
                "The same content is rendered in three formats that differ in form only. Level and importance "
                "are hidden by default: with the switch off the hierarchy has to emerge from the context; with "
                "it on the hierarchy is given."
            ),
            mo.hstack([cx_scenario, cx_repr, cx_lang, cx_importance], wrap=True),
        ]
    )
    return cx_importance, cx_lang, cx_repr, cx_scenario


@app.cell
def _(TEMPLATES, cx_importance, cx_lang, cx_repr, cx_scenario, cx_scenarios, mo, render):
    _s = cx_scenarios[cx_scenario.value]
    _text = render(_s, cx_repr.value, cx_lang.value, show_importance=cx_importance.value)
    _meta = (
        f"**{_s.title[cx_lang.value]}** ({_s.kind}, {_s.shape[0]} {_s.row_entity}s × {_s.shape[1]} opportunities"
        + (f", theory expects *{_s.expected}*" if _s.expected else "")
        + ")"
        + (f"  \n*Note: {_s.notes}*" if _s.notes else "")
    )
    mo.vstack(
        [
            mo.md(_meta),
            mo.hstack(
                [
                    mo.vstack([mo.md("**Template**"), mo.ui.code_editor(TEMPLATES[cx_repr.value], language="text", disabled=True)]),
                    mo.vstack([mo.md("**Rendered example**"), mo.ui.code_editor(_text, language="text", disabled=True)]),
                ],
                widths=[1, 2],
                wrap=True,
            ),
        ]
    )
    return


@app.cell
def _(cx_prompts, mo):
    cx_wording = mo.ui.dropdown(options=list(cx_prompts.WORDINGS), value="a", label="wording")
    cx_perspective = mo.ui.dropdown(options=list(cx_prompts.PERSPECTIVES), value="observer", label="perspective")
    cx_mode = mo.ui.dropdown(
        options={"one call per participant and opportunity": "pairwise", "one call per participant, all opportunities": "per_row"},
        value="one call per participant and opportunity",
        label="query mode",
    )
    cx_reason = mo.ui.switch(value=True, label="ask for a reason before the verdict")
    mo.vstack(
        [
            mo.md("### 5.3 Query syntax"),
            mo.md(
                "The system message fixes the task (eligibility only, nothing but the description, one JSON object) and the answer "
                "format; the user message carries the rendered description, the pair in question and the question. Placeholders: "
                "`{organization_description}`, `{participant}`, `{participant_description}`, `{opportunity}`, `{opportunity_list}`, "
                "`{answer_format}`. Where a provider offers a structured output mode the JSON schema below is sent along. Answers "
                "that are not a JSON object with a boolean `eligible` are counted as invalid and never replaced by a default."
            ),
            mo.hstack([cx_wording, cx_perspective, cx_mode, cx_reason], wrap=True),
        ]
    )
    return cx_mode, cx_perspective, cx_reason, cx_wording


@app.cell
def _(
    cx_lang,
    cx_mode,
    cx_perspective,
    cx_prompts,
    cx_reason,
    cx_repr,
    cx_scenario,
    cx_scenarios,
    cx_wording,
    entity_sentence,
    mo,
    render,
):
    import json as _json

    _s = cx_scenarios[cx_scenario.value]
    _t = cx_prompts.get_template(
        language=cx_lang.value,
        row_entity=_s.row_entity,
        perspective=cx_perspective.value,
        wording=cx_wording.value,
        mode=cx_mode.value,
        with_reason=cx_reason.value,
    )
    _row, _col = _s.rows[min(2, len(_s.rows) - 1)], _s.opportunities[min(1, len(_s.opportunities) - 1)]
    _system, _user = cx_prompts.build_prompt(
        _t,
        organization_description=render(_s, cx_repr.value, cx_lang.value),
        participant=_row.label[cx_lang.value],
        participant_description=entity_sentence(_row, cx_lang.value),
        opportunity=_col.label[cx_lang.value],
        opportunity_list="\n".join(f"- [{o.id}] {o.label[cx_lang.value]}" for o in _s.opportunities),
    )
    mo.vstack(
        [
            mo.md(f"Template hash `{_t.template_hash}` (identifies the query syntax in the logs). Expected answer: `{_t.answer_format}`"),
            mo.hstack(
                [
                    mo.vstack([mo.md("**System template**"), mo.ui.code_editor(_t.system, language="text", disabled=True)]),
                    mo.vstack([mo.md("**User template**"), mo.ui.code_editor(_t.user, language="text", disabled=True)]),
                ],
                wrap=True,
            ),
            mo.accordion(
                {
                    "JSON schema of the answer": mo.ui.code_editor(_json.dumps(_t.schema, indent=2), language="json", disabled=True),
                    f"One filled request ({_row.id} × {_col.id})": mo.ui.code_editor(
                        "SYSTEM\n" + _system + "\n\nUSER\n" + _user, language="text", disabled=True
                    ),
                }
            ),
        ]
    )
    return


@app.cell
def _(available_connectors, cx_prompts, mo):
    _configured = list(available_connectors())
    cx_connectors = mo.ui.multiselect(
        options=["mock", *_configured], value=["mock"], label="connectors (from .env; mock needs no API)"
    )
    cx_noise = mo.ui.slider(0, 0.5, 0.05, value=0.1, label="mock: probability of a flipped answer")
    cx_invalid = mo.ui.slider(0, 0.5, 0.05, value=0.0, label="mock: probability of an invalid answer")
    cx_reprs = mo.ui.multiselect(options=["prose", "role_list", "statute"], value=["prose"], label="representations")
    cx_langs = mo.ui.multiselect(options=["en", "de"], value=["en"], label="languages")
    cx_wordings = mo.ui.multiselect(options=list(cx_prompts.WORDINGS), value=["a"], label="wordings")
    cx_perspectives = mo.ui.multiselect(options=list(cx_prompts.PERSPECTIVES), value=["observer"], label="perspectives")
    cx_order = mo.ui.dropdown(options=["canonical", "shuffled"], value="canonical", label="item order (shuffled anew per loop)")
    cx_loops = mo.ui.slider(1, 30, 1, value=5, label="loops (repeated questions per pair)")
    cx_temperature = mo.ui.slider(0.0, 1.5, 0.1, value=0.7, label="temperature")
    cx_seed = mo.ui.number(0, 100_000, value=0, label="seed")
    cx_threshold = mo.ui.slider(0.05, 0.95, 0.05, value=0.5, label="binarization threshold")
    cx_run = mo.ui.run_button(label="Ask the models")
    mo.vstack(
        [
            mo.md("### 5.4 Controls"),
            mo.md(
                "Every combination of the selected factor levels is one configuration; each configuration is run with each "
                "selected connector. Answers already in the disk cache are reused, so pressing the button again never repeats a "
                "call. Query mode, reason switch, importance switch and scenario are taken from the controls above."
            ),
            mo.hstack([cx_connectors, cx_noise, cx_invalid], wrap=True),
            mo.hstack([cx_reprs, cx_langs, cx_wordings, cx_perspectives, cx_order], wrap=True),
            mo.hstack([cx_loops, cx_temperature, cx_seed, cx_threshold, cx_run], wrap=True),
        ]
    )
    return (
        cx_connectors,
        cx_invalid,
        cx_langs,
        cx_loops,
        cx_noise,
        cx_order,
        cx_perspectives,
        cx_reprs,
        cx_run,
        cx_seed,
        cx_temperature,
        cx_threshold,
        cx_wordings,
    )


@app.cell
def _(
    ExperimentConfig,
    cx_connectors,
    cx_importance,
    cx_langs,
    cx_loops,
    cx_mode,
    cx_order,
    cx_perspectives,
    cx_reason,
    cx_reprs,
    cx_scenario,
    cx_scenarios,
    cx_seed,
    cx_temperature,
    cx_wordings,
    expand_grid,
    mo,
    n_calls,
):
    _s = cx_scenarios[cx_scenario.value]
    cx_configs = expand_grid(
        ExperimentConfig(
            _s.id,
            item_order=cx_order.value,
            mode=cx_mode.value,
            with_reason=cx_reason.value,
            show_importance=cx_importance.value,
            loops=cx_loops.value,
            temperature=cx_temperature.value,
            seed=int(cx_seed.value),
        ),
        representation=cx_reprs.value or ["prose"],
        language=cx_langs.value or ["en"],
        wording=cx_wordings.value or ["a"],
        perspective=cx_perspectives.value or ["observer"],
    )
    _per_config = n_calls(_s, cx_configs[0])
    _total = _per_config * len(cx_configs) * max(1, len(cx_connectors.value))
    mo.md(
        f"**{_total} calls** before caching: {len(cx_configs)} configuration(s) × {max(1, len(cx_connectors.value))} connector(s) × "
        f"{_per_config} calls each ({_s.shape[0]} {_s.row_entity}s × "
        f"{_s.shape[1] if cx_mode.value == 'pairwise' else 1} × {cx_loops.value} loops)."
    )
    return (cx_configs,)


@app.cell
def _(
    DiskCache,
    MockConnector,
    available_connectors,
    cache_dir,
    cx_agg,
    cx_configs,
    cx_connectors,
    cx_invalid,
    cx_noise,
    cx_run,
    cx_scenario,
    cx_scenarios,
    mo,
    run_experiment,
    runs_dir,
):
    mo.stop(not cx_run.value, mo.md("*Press the button to query the models. Nothing is called on import or on a reactive re-run.*"))
    _s = cx_scenarios[cx_scenario.value]
    _factories = available_connectors()
    cx_estimates = {}
    cx_runs = {}
    _cache = DiskCache(cache_dir())
    _jobs = [(name, cfg) for name in (cx_connectors.value or ["mock"]) for cfg in cx_configs]
    with mo.status.progress_bar(total=len(_jobs), title="configurations") as _bar:
        for _name, _cfg in _jobs:
            if _name == "mock":
                if _s.target_matrix() is None:
                    raise ValueError(f"scenario {_s.id} has no expected structure, so the mock has nothing to answer from")
                _connector = MockConnector.for_scenario(_s, noise=cx_noise.value, invalid_rate=cx_invalid.value, seed=int(_cfg.seed))
            else:
                _connector = _factories[_name]()
            _result = run_experiment(_s, _cfg, _connector, cache=_cache, log_dir=runs_dir())
            _label = f"{_name} | {_cfg.label()}"
            cx_runs[_label] = _result
            cx_estimates[_label] = cx_agg.aggregate(
                _result.records, _s, label=_label, meta={"connector": _result.identity, "factors": _cfg.as_dict()}
            )
            _bar.update()
    _n_new = sum(r.n_new for r in cx_runs.values())
    _n_cached = sum(r.n_cached for r in cx_runs.values())
    _n_err = sum(r.n_errors for r in cx_runs.values())
    mo.md(
        f"{len(cx_runs)} run(s): {_n_new} new calls, {_n_cached} from the cache, {_n_err} failed. "
        f"Raw responses: `{runs_dir()}`; cache: `{cache_dir()}`."
    )
    return cx_estimates, cx_runs


@app.cell
def _(cx_estimates, mo):
    cx_pick = mo.ui.dropdown(options=list(cx_estimates), value=next(iter(cx_estimates)), label="estimate")
    mo.vstack([mo.md("### 5.5 Results"), cx_pick])
    return (cx_pick,)


@app.cell
def _(alt, cx_agg, cx_estimates, cx_lang, cx_pick, cx_scenario, cx_scenarios, cx_threshold, mo, np, pd):
    _s = cx_scenarios[cx_scenario.value]
    _e = cx_estimates[cx_pick.value]
    _low, _high = _e.wilson()
    _uncertain = cx_agg.uncertain_cells(_e, cx_threshold.value)
    _rows = []
    for _r, _rid in enumerate(_s.row_ids):
        for _c, _cid in enumerate(_s.col_ids):
            _rows.append(
                {
                    "participant": _s.rows[_r].label[cx_lang.value],
                    "opportunity": _s.opportunities[_c].label[cx_lang.value],
                    "yes share": _e.share[_r, _c],
                    "valid n": int(_e.valid[_r, _c]),
                    "invalid": int(_e.invalid[_r, _c] + _e.errors[_r, _c]),
                    "wilson low": _low[_r, _c],
                    "wilson high": _high[_r, _c],
                    "uncertain": bool(_uncertain[_r, _c]),
                }
            )
    _df = pd.DataFrame(_rows)
    _heat = (
        alt.Chart(_df)
        .mark_rect(stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("opportunity:N", sort=list(_s.col_labels(cx_lang.value)), title="opportunity (importance order)"),
            y=alt.Y("participant:N", sort=list(_s.row_labels(cx_lang.value)), title=f"{_s.row_entity} (importance order)"),
            color=alt.Color("yes share:Q", scale=alt.Scale(scheme="blues", domain=[0, 1]), title="yes share"),
            tooltip=["participant", "opportunity", alt.Tooltip("yes share:Q", format=".2f"), "valid n", "invalid",
                     alt.Tooltip("wilson low:Q", format=".2f"), alt.Tooltip("wilson high:Q", format=".2f"), "uncertain"],
        )
        .properties(width=min(600, 48 * len(_s.col_ids) + 60), height=min(600, 28 * len(_s.row_ids) + 40),
                    title="yes share per cell (Wilson interval in the tooltip)")
    )
    _binary = pd.DataFrame(
        np.where(np.isnan(_e.share), "?", np.where(_e.share >= cx_threshold.value, "1", "0")),
        index=_s.row_ids, columns=_s.col_ids,
    )
    _known = ~np.isnan(_e.share)
    _degenerate = cx_agg.degeneracy(_e.share >= cx_threshold.value, _s.row_ids, _s.col_ids) if _known.all() else None
    _notes = [
        f"**{_e.n_answers} answers**, {_e.invalid.sum()} invalid and {_e.errors.sum()} failed ({_e.invalid_share:.1%}); "
        f"{int(_uncertain.sum())} of {_uncertain.size} cells uncertain at threshold {cx_threshold.value:.2f} "
        f"(interval contains the threshold or no valid answer)."
    ]
    if _degenerate is None:
        _notes.append("Some cells have no valid answer (`?`); the structure cannot be exported until they are answered.")
    elif _degenerate["rows_without_opportunity"] or _degenerate["opportunities_without_row"]:
        _notes.append(f"**Degenerate structure:** rows without any opportunity {_degenerate['rows_without_opportunity']}, "
                      f"opportunities nobody may enter {_degenerate['opportunities_without_row']}. Reported, not repaired.")
    mo.vstack(
        [
            mo.md(" ".join(_notes)),
            mo.hstack([_heat, mo.vstack([mo.md(f"**Binary structure** (share ≥ {cx_threshold.value:.2f})"), _binary])], wrap=True),
        ]
    )
    return


@app.cell
def _(cx_agg, cx_estimates, cx_scenario, cx_scenarios, cx_threshold, mo, reference_matrices):
    _s = cx_scenarios[cx_scenario.value]
    _refs = reference_matrices(*_s.shape)
    _dist = cx_agg.distance_table(cx_estimates, _refs, cx_threshold.value).round(3)
    _agree = cx_agg.agreement_table(cx_estimates, cx_threshold.value).round(3)
    _expect = f" Theory expects *{_s.expected}* for this scenario." if _s.expected else ""
    mo.vstack(
        [
            mo.md(
                "**Distance to the three reference structures** (share of differing binary cells; the non-square forms of the references "
                f"compare ranks as fractions of their axis).{_expect}"
            ),
            _dist,
            mo.md("**Agreement across models and representations** (share of identical cells, Cohen's kappa, mean absolute difference of the yes shares)."),
            _agree if len(_agree) else mo.md("*Only one estimate; select several connectors or factor levels to compare.*"),
        ]
    )
    return


@app.cell
def _(StructureExport, cx_estimates, cx_lang, cx_pick, cx_scenario, cx_scenarios, cx_threshold, mo, structures_dir):
    import re as _re

    _s = cx_scenarios[cx_scenario.value]
    cx_export = StructureExport.from_estimate(
        cx_estimates[cx_pick.value], _s, threshold=cx_threshold.value, on_missing="error", language=cx_lang.value,
        name=cx_pick.value,
    )
    cx_file = structures_dir() / (_re.sub(r"[^A-Za-z0-9.]+", "-", f"{_s.id}__{cx_pick.value}").strip("-") + ".json")
    cx_save = mo.ui.run_button(label="Save the selected structure")
    mo.vstack([mo.md(f"The selected estimate as a structure file (both matrices, labels, provenance): `{cx_file}`"), cx_save])
    return cx_export, cx_file, cx_save


@app.cell
def _(cx_export, cx_file, cx_save, mo):
    mo.stop(not cx_save.value, mo.md("*Not saved yet. The comparison below uses the selected structure directly.*"))
    cx_export.save(cx_file)
    mo.md(f"Saved `{cx_file}`.")
    return


@app.cell
def _(mo):
    cx_f_levels = mo.ui.slider(1, 5, 1, value=2, label="hierarchy levels (groups of ranks)")
    cx_f_sample = mo.ui.switch(value=True, label="also run the probabilistic mode (one draw per situation)")
    cx_f_run = mo.ui.run_button(label="Run the FORTRAN comparison")
    mo.vstack(
        [
            mo.md("### 5.6 Simulation comparison"),
            mo.md(
                "**FORTRAN port.** The program is deterministic, so the replication unit is the situation: every decision structure is run "
                "over the same 108 situations (3 loads × 3 access structures × 3 energy distributions × 4 entry conditions). The rule-based "
                "structures D0, D1 and D2 are the baselines; the contextual structure is the one selected above (10 × 10 scenarios only). "
                "Decision styles are compared with a chi-square test on the pooled counts and Cramér's V; the other metrics with means, "
                "bootstrap intervals over situations, paired differences, Cohen's d and a Wilcoxon test."
            ),
            mo.hstack([cx_f_levels, cx_f_sample, cx_f_run], wrap=True),
        ]
    )
    return cx_f_levels, cx_f_run, cx_f_sample


@app.cell
def _(alt, cx_cp, cx_export, cx_f_levels, cx_f_run, cx_f_sample, mo, pd):
    mo.stop(not cx_f_run.value, mo.md("*Press the button; 4 to 5 structures × 108 situations take a few seconds.*"))
    mo.stop(cx_export.shape != (10, 10), mo.md(f"*The selected structure is {cx_export.shape}; the FORTRAN port needs 10 × 10.*"))
    _conditions = [*cx_cp.fortran_reference_conditions(), cx_cp.FortranCondition("contextual (threshold)", export=cx_export)]
    if cx_f_sample.value:
        _conditions.append(cx_cp.FortranCondition("contextual (sampled)", export=cx_export, mode="sample"))
    cx_f_results = cx_cp.run_fortran_conditions(_conditions, n_levels=cx_f_levels.value)
    _styles = cx_cp.style_table(cx_f_results).round(3)
    _chi = cx_cp.style_chi_square(cx_f_results)
    _chi_ctx = cx_cp.style_chi_square(cx_f_results, conditions=["D_unsegmented", "contextual (threshold)"])
    _levels = list(range(1, cx_f_levels.value + 1))
    _metrics = ["proportion_resolution", "problem_latency", "choice_persistence", "problems_not_solved"] + [
        f"{m}_L{k}" for k in _levels for m in ("resolution_share", "problems_solved_share", "problem_latency", "time_to_solution")
    ]
    _cmp = cx_cp.compare_metrics(cx_f_results, _metrics, "D_unsegmented", paired_on="situation").round(3)
    _long = cx_f_results.melt(
        id_vars=["condition"], value_vars=[f"resolution_share_L{k}" for k in _levels], var_name="level", value_name="resolution share"
    )
    _chart = (
        alt.Chart(_long)
        .mark_bar()
        .encode(
            x=alt.X("level:N", title=None), y=alt.Y("mean(resolution share):Q", title="mean resolution share"),
            color=alt.Color("condition:N", sort=list(_styles.index)), column=alt.Column("condition:N", sort=list(_styles.index), title=None),
            tooltip=["condition", "level", alt.Tooltip("mean(resolution share):Q", format=".3f")],
        )
        .properties(width=90, height=180)
    )
    mo.vstack(
        [
            mo.md(f"**Decision styles, pooled over 108 situations.** Chi-square over all conditions: χ² = {_chi.chi2:.1f}, df = {_chi.dof}, "
                  f"p = {_chi.p_value:.2g}, Cramér's V = {_chi.cramers_v:.3f}. Unsegmented vs. contextual (threshold): χ² = {_chi_ctx.chi2:.1f}, "
                  f"p = {_chi_ctx.p_value:.2g}, V = {_chi_ctx.cramers_v:.3f}."),
            _styles,
            mo.md("**Resolution share per hierarchy level** (level 1 = most important choices)."),
            _chart,
            mo.md("**Metrics against D0 (unsegmented)**, paired by situation: mean with bootstrap interval, difference with interval, Wilcoxon p, Cohen's d."),
            mo.ui.table(_cmp, selection=None, page_size=12),
        ]
    )
    return (cx_f_results,)


@app.cell
def _(mo):
    cx_n_ticks = mo.ui.slider(500, 20_000, 500, value=2000, label="ticks per run")
    cx_n_seeds = mo.ui.slider(2, 30, 1, value=4, label="seeds (shared by all conditions)")
    cx_n_workers = mo.ui.slider(1, 16, 1, value=2, label="worker processes")
    cx_n_mapping = mo.ui.dropdown(options=["random", "ranked", "inverse"], value="random", label="roles onto abilities")
    cx_n_sample = mo.ui.switch(value=False, label="probabilistic mode (one draw per run)")
    cx_n_run = mo.ui.run_button(label="Run the NetLogo comparison")
    mo.vstack(
        [
            mo.md(
                "**NetLogo port.** All conditions are run with the same seeds, so the baseline and the contextual variant start from the "
                "same agents at the same positions. The role × type matrix of the selected structure is expanded to the 100 participants "
                "and 100 opportunities: equal shares unless the scenario's `assignment` block says otherwise, the most important type "
                "takes the lowest `who` numbers, and roles map onto abilities at random, ranked (ablest participants in the most important "
                "role) or inversely. The contextual structure is run twice, with the availability and access structures unrestricted "
                "(isolates the component) and with them set as in the competent hierarchy (BehaviorSpace-like). Flights stay on."
            ),
            mo.hstack([cx_n_ticks, cx_n_seeds, cx_n_workers, cx_n_mapping, cx_n_sample, cx_n_run], wrap=True),
        ]
    )
    return cx_n_mapping, cx_n_run, cx_n_sample, cx_n_seeds, cx_n_ticks, cx_n_workers


@app.cell
def _(
    NetLogoParameters,
    RoleAssignment,
    Structure,
    alt,
    cx_cp,
    cx_export,
    cx_n_mapping,
    cx_n_run,
    cx_n_sample,
    cx_n_seeds,
    cx_n_ticks,
    cx_n_workers,
    cx_scenario,
    cx_scenarios,
    mo,
):
    mo.stop(not cx_n_run.value, mo.md("*Press the button; about 1.4 ms per tick and run, five conditions.*"))
    _s = cx_scenarios[cx_scenario.value]
    _assignment = RoleAssignment.for_export(cx_export, **(_s.assignment or {}), ability_mapping=cx_n_mapping.value)
    _base = NetLogoParameters(stop_at=cx_n_ticks.value)
    _mode = "sample" if cx_n_sample.value else "threshold"
    _conditions = [
        cx_cp.NetLogoCondition("unrestricted", _base.with_structures(Structure.ORGANIZED_ANARCHY)),
        cx_cp.NetLogoCondition("competent", _base.with_structures(Structure.COMPETENT_HIERARCHY)),
        cx_cp.NetLogoCondition("incompetent", _base.with_structures(Structure.INCOMPETENT_HIERARCHY)),
        cx_cp.NetLogoCondition(
            "contextual | others unrestricted", _base.with_structures(Structure.ORGANIZED_ANARCHY),
            export=cx_export, assignment=_assignment, mode=_mode,
        ),
        cx_cp.NetLogoCondition(
            "contextual | others competent", _base.with_structures(Structure.COMPETENT_HIERARCHY),
            export=cx_export, assignment=_assignment, mode=_mode,
        ),
    ]
    cx_n_results = cx_cp.run_netlogo_conditions(_conditions, seeds=range(cx_n_seeds.value), ticks=cx_n_ticks.value, workers=cx_n_workers.value)
    _styles = cx_cp.style_table(cx_n_results, cx_cp.NETLOGO_STYLES).round(3)
    _chi = cx_cp.style_chi_square(cx_n_results, cx_cp.NETLOGO_STYLES)
    _metrics = [
        "share_resolutions", "decisions", "flights", "ave_duration_blocked",
        "resolution_share_L1", "resolution_share_L2", "decisions_L1", "decisions_L2", "blocked_for_L1", "blocked_for_L2",
    ]
    _cmp = cx_cp.compare_metrics(cx_n_results, _metrics, "unrestricted", paired_on="seed").round(3)
    _long = cx_n_results.melt(
        id_vars=["condition", "seed"], value_vars=["resolution_share_L1", "resolution_share_L2"], var_name="level", value_name="resolution share"
    )
    _chart = (
        alt.Chart(_long)
        .mark_point(filled=True, size=60)
        .encode(
            x=alt.X("level:N", title=None), y=alt.Y("resolution share:Q"),
            color=alt.Color("condition:N", sort=list(_styles.index)), column=alt.Column("condition:N", sort=list(_styles.index), title=None),
            tooltip=["condition", "seed", "level", alt.Tooltip("resolution share:Q", format=".3f")],
        )
        .properties(width=90, height=180)
    )
    _demo = _conditions[3].build(0)
    mo.vstack(
        [
            mo.md(f"**Decision styles, pooled over {cx_n_seeds.value} seeds × {cx_n_ticks.value} ticks.** Chi-square over all conditions: "
                  f"χ² = {_chi.chi2:.1f}, df = {_chi.dof}, p = {_chi.p_value:.2g}, Cramér's V = {_chi.cramers_v:.3f}. "
                  "Flights are events, not decisions; they appear as metrics below."),
            _styles,
            mo.md("**Resolution share per importance level, one point per seed** (level 1 = `who ≤ hierarchy-divide`)."),
            _chart,
            mo.md("**Metrics against the unrestricted baseline**, paired by seed."),
            mo.ui.table(_cmp, selection=None, page_size=10),
            mo.accordion(
                {
                    "Role assignment of the contextual condition (seed 0)": mo.vstack(
                        [_demo.components.decision_structure.assignment_table(_demo), _demo.components.decision_structure.type_table(_demo)]
                    )
                }
            ),
        ]
    )
    return (cx_n_results,)


if __name__ == "__main__":
    app.run()

