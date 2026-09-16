import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium", app_title="Garbage Can Model")


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
    (a Python `Protocol`). Only rule-based implementations exist at this stage: the seams are
    where the LLM-agent substitutes of the thesis (decision/access structure, optionally energy
    allocation) will later be plugged in without touching the simulation cores. Section 3
    documents them.
    """)


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


@app.cell
def _(f_history, format_histories, mo):
    mo.accordion(
        {
            "Histories as printed by the program under IO = 2 (choice activation, decision maker activity, problem history)": mo.ui.code_editor(
                format_histories(f_history), language="text", disabled=True
            )
        }
    )


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


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Architecture: where the LLM agents will plug in

    Both packages separate the *simulation core* (streams, meetings, energy accounting,
    histories) from the *behavioural assumptions*, each of which is a `Protocol` with a
    rule-based default. The thesis substitutes the decision and access structures (research
    question 1) and optionally the energy allocation; the other seams are there so that the
    remaining assumptions can be varied in the same way. Nothing LLM-related is implemented
    yet; the table lists the exact methods a substitute has to provide.

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


if __name__ == "__main__":
    app.run()
