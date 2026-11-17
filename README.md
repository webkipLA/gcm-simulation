# gcm: the Garbage Can Model in Python, with a decision structure written by language models

Code and data for the bachelor's thesis *Simulation ausgewählter Bestandteile des
Entscheidungsprozesses im Garbage-Can-Modell mit generativen KI-/LLM-Agenten* (Leon Adel,
TH Köln, 2026).

## What this repository does

The Garbage Can Model (GCM) simulates how decisions come about in an organization. One of its
inputs is the *decision structure*: a table that says which participant may take part in which
choice opportunity. In the published models this table is set by a rule.

The thesis lets a language model write this table from a text that describes the organization.
It then asks three questions:

- **FF1** Do the Python simulations reproduce the published models at all?
- **FF2** Does the language model get the table right?
- **FF3** What happens in the simulation when the table differs, and how robust is that?

The whole pipeline in one picture:

```
text describing an organization              src/gcm/contextual/scenarios/*.yaml
      |   a language model is asked several times who may take part where
      v
raw answers                                  data/llm_runs/*.jsonl
      |   share of "yes" per cell, threshold 0.5
      v
decision structure (a table of 0 and 1)      data/structures/*.json
      |   replaces the rule-based table, everything else stays as published
      v
simulation                                   src/gcm/fortran  (Cohen, March & Olsen 1972)
      |                                      src/gcm/netlogo  (Fioretti & Lomi, NetLogo model)
      v
tables and figures of chapter 4              data/analysis/
```

The simulations never call a language model. They only load a stored table, so every
simulation result can be computed again without an API key.

## Install

The only requirement is [uv](https://docs.astral.sh/uv/). It installs Python 3.11 and all
dependencies into a local `.venv`.

```bash
git clone https://github.com/webkipLA/gcm-simulation
cd gcm-simulation
uv sync --all-groups
uv run pytest -q          # 191 tests, two to four minutes, no network and no API key needed
```

All commands in this file are run from the repository root. They work unchanged in PowerShell
on Windows.

## Two ways to use it

| | The notebook | The scripts |
|---|---|---|
| Good for | looking at the two models, trying settings, following the pipeline once by hand | producing the results of the thesis |
| Start with | `uv run marimo run notebooks/gcm_notebook.py` | `uv run gcm-fortran`, then the section "Reproducing the thesis" |
| API key | not needed, a built-in mock stands in for the language model | only needed to ask the language models again |
| Run length | short runs by default, seconds to a few minutes | the full runs of the thesis, up to hours |

Both use the same code under `src/gcm` and the same folders under `data/`. The notebook is a
front end for exploring. The runs of the thesis are defined in the scripts, so that each can be
repeated with one command.

## The notebook

```bash
uv run marimo run notebooks/gcm_notebook.py     # opens in the browser as an app with controls
uv run marimo edit notebooks/gcm_notebook.py    # the same, with the code of every cell visible
```

[marimo](https://marimo.io) notebooks are plain Python files. Changing a control recomputes
the cells that depend on it. Long computations wait for a button.

| Section | What it shows | What to do |
|---|---|---|
| 1.1 The FORTRAN model, one situation | one of the 324 situations of the 1972 paper with its decision styles and summary statistics | choose load, structures and energy distribution in the dropdowns; the run takes milliseconds |
| 1.2 Docking | the port's values next to the published tables | nothing, it is computed when the notebook opens |
| 2.1 The agent-based model, one run | one run of the NetLogo port with the sliders of the original interface | press **Run the agent-based model** |
| 2.2 BehaviorSpace experiments | the twelve experiments of the model, shortened | press **Run the 12 experiments** |
| 3. Architecture | which part of each model can be replaced, and through which interface | read |
| 4. Notes on fidelity | where the ports had to interpret the originals | read |
| 5. A contextual decision structure | the LLM component step by step: the scenario as text (5.2), the exact prompt (5.3), asking the models (5.4), the resulting table and its distance to the expected one (5.5), the simulation with that table against the rule-based ones (5.6) | press **Ask the models**, then **Run the FORTRAN comparison** or **Run the NetLogo comparison**; **Save the selected structure** writes the table to `data/structures/` |

Section 5 works without any setup: the connector `mock` answers from the expected table with a
little noise, so the whole pipeline can be followed. Real models appear in the connector list
once they are configured in `.env` (see "Configuration"). Answers are cached on disk, so
pressing a button twice never repeats a call, and the notebook and the scripts share that
cache.

The notebook writes into the same `data/` folders as the scripts. To explore without touching
the stored data, point it to another folder first: `GCM_DATA_DIR=scratch` (PowerShell:
`$env:GCM_DATA_DIR = "scratch"`).

## Reproducing the thesis

Five scripts, in the order of the thesis. Steps 1 and 4 need nothing but this repository.

| Step | Question | Script | Needs | Time |
|---|---|---|---|---|
| 1 | FF1: do the ports reproduce the published models? | `run_docking.py` | nothing | seconds; two hours with the NetLogo port |
| 2 | FF1: port against the original NetLogo model | `netlogo_original.py` | NetLogo 7.0.4 | 360 NetLogo runs |
| 3 | FF2: tables from language models | `run_batch.py` | API key or local Ollama | minutes to hours |
| 4 | FF2, FF3: every table and figure of chapter 4 | `analyse_results.py` | nothing, uses the stored answers | minutes |
| 5 | FF3: transfer to the NetLogo port | `run_netlogo_llm.py` | 90 model calls, then CPU time | 100 runs of about 70 s |

A note on step 3: asking the models again does not give the numbers of the thesis exactly. The
models answer at temperature 0.7, hosted models can change on the provider's side, and a new
call is a new sample. This is why the raw answers of the thesis are stored in `data/llm_runs/`.
Steps 1 and 4 start from stored data and give the same numbers every time.

### Step 1: docking of the ports (FF1)

```bash
uv run gcm-fortran
uv run python scripts/run_docking.py --reference data/reference/GCM_Referenzdaten_CMO1972_Fioretti2008.xlsx --skip-netlogo --out data/docking_check
```

The first command runs the 324 situations of the 1972 paper and prints Tables 1 and 2 next to
the published values. The second compares all 101 published values with the port. Expected last
lines:

```
[exact] {'identisch im Rahmen der Rundung': 47, 'innerhalb Toleranz': 33, 'Abweichung': 21}
report: data/docking_check/docking_report.md
```

`--out` keeps the stored report in `data/docking/` untouched. The stored report was produced
with both arithmetics and the NetLogo port:

```bash
uv run python scripts/run_docking.py --reference data/reference/GCM_Referenzdaten_CMO1972_Fioretti2008.xlsx --arithmetic exact ibm360 --netlogo-ticks 50000 --netlogo-seeds 30
```

The comparison of the initial requirement of a choice opportunity (1.1 in the original source
text, against 0 and 1.0; appendix of the thesis):

```bash
uv run python scripts/run_docking.py --reference data/reference/GCM_Referenzdaten_CMO1972_Fioretti2008.xlsx --skip-netlogo --initial-requirement 1.1 0 1.0 --out data/docking_initial_requirement
```

### Step 2: the original NetLogo model against the port (FF1)

`data/netlogo_original/GarbageCan_fioretti.nlogox` is the model file the port follows.
`GarbageCan_simplified17_headless.nlogox` is a copy with the same model code whose
BehaviorSpace experiments are set to 30 repetitions and to the same 13 reported quantities for
every experiment.

```bash
uv run python scripts/netlogo_original.py prepare --model data/netlogo_original/GarbageCan_fioretti.nlogox
NETLOGO=/path/to/NetLogo_Console ./data/netlogo_original/run_original.sh     # Windows: .\data\netlogo_original\run_original.ps1
uv run python scripts/netlogo_original.py compare
```

The first two commands need NetLogo 7.0.4. The tables NetLogo wrote for the thesis are stored
in `data/netlogo_original/tables/`, so `compare` can be run on its own. Result:
`data/netlogo_original/report.md`. BehaviorSpace sets no seeds, so the comparison is
between distributions, not between individual runs.

### Step 3: tables from language models (FF2)

Copy `.env.example` to `.env` and enter the key or the local model. `--dry-run` prints the plan
and how many calls are already answered, without calling a model:

```bash
uv run python scripts/run_batch.py --connector gemini/gemini-3.5-flash-lite --mode per_row --university --dry-run
```

The runs of the thesis. Every line starts with
`uv run python scripts/run_batch.py --mode per_row` (one call per participant, ten per loop):

| Model and setting | Rest of the command | Calls |
|---|---|---|
| Main model gemini-3.5-flash-lite, thinking level `minimal` | `--connector gemini/gemini-3.5-flash-lite --university` | 720 |
| same, university scenario without the participation statement | `--connector gemini/gemini-3.5-flash-lite --stages university_np` | 150 |
| same, university scenario with shuffled item order | `--connector gemini/gemini-3.5-flash-lite --stages university_audit --audit item_order=shuffled` | 60 |
| Main model with thinking level `low`, university scenario | `--connector gemini/gemini-3.5-flash-lite --stages university --thinking-level low` | 150 |
| gemini-4-argon, thinking level `low` (the model rejects `minimal`) | `--connector gemini/gemini-4-argon --stages core university --thinking-level low` | 300 |
| qwen3:4b via Ollama, thinking off | `--connector ollama/qwen3:4b --stages core det` | 210 |
| same, audit | `--connector ollama/qwen3:4b --stages audit` | 360 |
| same, three audit factors with five loops for the hierarchical form | `--connector ollama/qwen3:4b --stages audit --scenarios reference_hierarchical --audit wording=b item_order=shuffled perspective=persona --side-loops 5` | 90 more |

The stages: `core` asks about the three reference scenarios five times at temperature 0.7,
`det` twice at temperature 0, `audit` changes one prompt factor at a time, `university` asks
about the three variants of the university scenario. The main-model runs used
`GEMINI_THINKING_LEVEL=minimal` and the qwen runs `OLLAMA_THINK=false` in `.env`. A
supplementary run of qwen3:8b (hierarchical reference scenario, 500 calls) used the pairwise
mode, which asks about every pair of participant and opportunity separately.

A run can be stopped and restarted at any time; answered calls are never asked again. Output:
raw answers in `data/llm_runs/*.jsonl`, one table per configuration in
`data/structures/batch/`, one summary row per configuration in
`data/batch/summary__<connector>.csv`. `uv run python scripts/run_batch.py --help` describes
all stages and flags.

To try the script without any model: `uv run python scripts/run_batch.py --connector mock`.

### Step 4: the analysis of chapter 4 (FF2 and FF3)

```bash
uv run python scripts/analyse_results.py --null 0             # everything except the null model (fast)
uv run python scripts/analyse_results.py                      # with the null model, 200 draws
uv run python scripts/analyse_results.py --arithmetic ibm360  # all FORTRAN comparisons with the second arithmetic
```

Reads the stored answers in `data/llm_runs/` and the stored runs of the NetLogo port, runs
every table through the FORTRAN port over the 108 situations, and writes tables, figures and
`report.md` to `data/analysis/`. With `--arithmetic ibm360` the output goes to
`data/analysis__ibm360/`, and `arithmetic_comparison.md` sets the two side by side.

### Step 5: transfer check in the NetLogo port (FF3)

```bash
uv run python scripts/run_netlogo_llm.py llm --connector gemini/gemini-3.5-flash-lite
uv run python scripts/run_netlogo_llm.py sim --connector gemini/gemini-3.5-flash-lite --ticks 50000 --seeds 10 --workers 6
uv run python scripts/run_netlogo_llm.py sim --connector gemini/gemini-3.5-flash-lite --ticks 50000 --seeds 10 --workers 6 --exclusion-controls
```

The `llm` step asks about the role scenario (90 calls) and stores the answers in the local
cache. The `sim` step needs these answers and a configured connector name, but makes no model
call. The cache of the thesis run is not part of the repository. Its three tables are in
`data/structures/roles/`, its simulation runs in `data/netlogo_llm/runs_*.csv`, and its reports
in `data/netlogo_llm/report_ranked_50000t_10s*.md`.

## Where the results of the thesis are

These files are part of the repository and can be read without running anything.

| Thesis | File | Written by |
|---|---|---|
| 4.1, docking of the FORTRAN port, both arithmetics; docking of the NetLogo port | `data/docking/docking_report.md` | `run_docking.py` |
| Appendix, initial requirement 1.1, 0 and 1.0 | `data/docking_initial_requirement/docking_report.md` | `run_docking.py` |
| 4.1, original NetLogo model against the port | `data/netlogo_original/report.md` | `netlogo_original.py` |
| 4.2, structural fidelity per model, scenario and configuration | `data/analysis/report.md`, section FF2 | `analyse_results.py` |
| 4.3, decision styles and paired comparisons in the FORTRAN port, null model | `data/analysis/report.md`, sections FF3 | `analyse_results.py` |
| 4.3, the same comparisons with the arithmetic `ibm360` | `data/analysis__ibm360/arithmetic_comparison.md` | `analyse_results.py` |
| 4.3, transfer check and its control conditions | `data/netlogo_llm/report_ranked_50000t_10s*.md` | `run_netlogo_llm.py` |
| Figures of chapter 4 | `data/analysis/figures/abb_4_1` to `abb_4_8` (PDF and PNG) | `analyse_results.py` |
| Scenario texts (appendix B) | `src/gcm/contextual/scenarios/*.yaml` | |
| Prompt templates (appendix B) | `src/gcm/contextual/prompts.py` | |
| Published values used as docking targets | `data/reference/GCM_Referenzdaten_CMO1972_Fioretti2008.xlsx` | |
| The tables used in the simulations | `data/structures/batch/`, `data/structures/roles/` | `run_batch.py`, `run_netlogo_llm.py` |

The reports use the German terms of the thesis in their headings. The code and its
documentation are in English. The reports also contain statistics that the thesis does not
report (pooled chi-square tests, Cramér's V, Cohen's d).

**What is stored and what is not.** The repository keeps only what cannot be produced again
cheaply: the raw answers of the language models, the tables derived from them, the long runs of
the NetLogo port and of the original NetLogo model, and the reports. All other tables are
written again by the scripts within minutes and are not tracked.

## Configuration

Language models are configured through environment variables or a git-ignored `.env` file
(template: `.env.example`).

| Connector | Variables | Used as |
|---|---|---|
| Google Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_THINKING_LEVEL`, `GEMINI_RPM` | `--connector gemini/<model>` |
| Local Ollama | `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_THINK` | `--connector ollama/<model>` |
| Any OpenAI-compatible endpoint | `UNI_API_BASE_URL`, `UNI_API_KEY`, `UNI_API_MODEL` | `--connector uni/<model>` |
| Mock, no model | none | `--connector mock` |

Model, thinking setting, temperature, seed and the full prompt are part of every cache key, so
answers obtained with different settings are never mixed.

## Reference

### Layout

```
src/gcm/
  common/            DecisionStyle (resolution / oversight / flight), StructureKind
  fortran/
    data.py          entry-time cards and solution coefficients of the paper
    parameters.py    fixed parameters, load, movement condition NA, arithmetic backend
    state.py         all arrays of the program (XERC, XEE, JF, KDC, ...)
    interfaces.py    Protocols: DecisionStructure, AccessStructure, EnergyDistribution,
                     ProblemAllocationRule, DecisionMakerAllocationRule, ChoiceRule
    structures.py    the nine structures D0-2, A0-2, E0-2; OrganizationalVariant (81 codes)
    allocation.py    closest-to-decision allocation rules, energy additivity rule
    arithmetic.py    exact / float64 / IBM System/360 emulation backends
    model.py         the period loop (statement numbers of the original cited inline)
    statistics.py    the ten summary statistics, decision-style tagging, history printout
    experiments.py   run_all (324 runs), Tables 1, 2 and 5 next to the published values
  netlogo/
    parameters.py    all interface parameters, the 12 BehaviorSpace experiments
    agents.py        the four breeds, patch colours as state
    hierarchy.py     assign-importance (pyramid, hierarchy divide)
    interfaces.py    Protocols: DecisionStructure, AvailabilityStructure, AccessStructure,
                     ResolutionRule, FlightSelector
    structures.py    organized anarchy / competent / incompetent hierarchy movement rules
    rules.py         resolution inequality, most-difficult-to-latest-arrival flights
    model.py         setup / go: decision-making, flights, movement, monitor
    experiments.py   BehaviorSpace-style runs (multiprocess), sweeps
  contextual/        the LLM component
    scenario.py      scenarios as YAML data files (ordered participants and opportunities, variants)
    scenarios/       reference scenarios (the three structures in plain language), the
                     university scenario (10 x 10) and the role scenario (6 x 5)
    representation.py  prose, role list and statute renderings; importance switch; item order
    prompts.py       system and user templates (wording, perspective, language, query mode),
                     JSON answer and schema, guard against theory terms in prompts
    connectors/      one interface; Ollama, OpenAI-compatible, Gemini, Mock
    cache.py, runlog.py  disk cache keyed by the full request; raw responses as JSON Lines
    experiment.py    factor grid, call planning (count before running), the runner
    aggregate.py     yes share, valid n, Wilson interval, threshold or sampled binarization,
                     degeneracy report, agreement (kappa), distances to the expected matrices
    structure_io.py  the exported structure file (probability matrix, binary matrix, provenance)
    fortran_adapter.py   DecisionStructure.matrix(state) backed by an export
    netlogo_adapter.py   role x type export expanded to agents
    metrics.py       per-level metrics for both ports (styles, latencies, resolution rates)
    compare.py       baselines and LLM structures over identical situations or seeds: paired
                     differences, bootstrap intervals and tests
scripts/             the five scripts of "Reproducing the thesis", plus check_ollama.py
                     (speed check of a local model)
notebooks/gcm_notebook.py   the marimo notebook
tests/               matrices against the printed arrays, Table 5 rows, docking tolerances,
                     mechanics, and the LLM pipeline end to end with the Mock connector
data/                reference values, stored answers and tables, and the reports listed above
```

### How the LLM component works

1. A scenario (`src/gcm/contextual/scenarios/*.yaml`) is rendered as text in one of three
   formats.
2. A language model is asked, several times, whether a participant is *permitted* to take part
   in an opportunity. It judges eligibility only, never whether the participant would want to
   attend. The answer is a JSON object such as `{"reason": "...", "eligible": true}`. Invalid
   answers are counted, never replaced by a default.
3. The answers become a yes share per cell and a binary matrix, by threshold (default 0.5) or by
   drawing one matrix per simulation run.
4. The matrix is exported to `data/structures/` and loaded by the simulations through the
   existing interfaces (`ContextualDecisionStructure` for the FORTRAN port, 10 x 10;
   `ContextualNetLogoDecisionStructure` for the NetLogo port, which expands a small role x type
   matrix to the agents).
5. Rule-based matrices and LLM structures are run over the same situations (FORTRAN) or seeds
   (NetLogo) and compared.

Prompts never mention the garbage can model, the organization type of the 1972 paper or the
names of the structures.

### Extension points

Both ports keep every behavioural assumption in a small, swappable component with a rule-based
default. A substitute is any object with the listed methods and a `name`, handed to the model
via `FortranComponents` or `NetLogoComponents`.

| Aspect of the GCM | FORTRAN port | NetLogo port |
|---|---|---|
| Decision structure (**replaced by `gcm.contextual`**) | `DecisionStructure.matrix(state)` | `DecisionStructure.participant_may_enter(...)` / `.opportunity_may_enter(...)` |
| Access structure | `AccessStructure.matrix(state)` | `AccessStructure.problem_may_enter(...)` / `.opportunity_may_enter(...)` |
| Availability structure (solutions) | not in the original model | `AvailabilityStructure.solution_may_enter(...)` / `.opportunity_may_enter(...)` |
| Energy allocation of decision makers | `DecisionMakerAllocationRule.choose(dm, state)` | random walk |
| Problem allocation | `ProblemAllocationRule.choose(problem, state)` | random walk |
| Energy distribution | `EnergyDistribution.matrix(n_dm, n_periods, arith)` | uniform draw at setup |
| Decision rule | `ChoiceRule.is_made(choice, state)` | `ResolutionRule.resolves(here, model)` |
| Flights | emergent | `FlightSelector.postponement(...)` / `.buck_passing(...)` |

### Fidelity notes

**FORTRAN.** The original source text is reproduced block by block; the statement numbers of
the original are cited in the code. The program does not compute decision styles. They are
derived from the run histories following the definitions on p. 8 of the paper (resolution if
problems are attached when the choice is made, flight if problems had been attached earlier,
oversight otherwise). Two details are exposed as parameters: the initial requirement of a fresh
choice (`initial_choice_requirement`, 1.1) and the arithmetic used to decide ties. The paper's
parameter space is full of exact ties (three light-load problems need 3 x 1.1 = 3.3, ten equal
decision makers supply 10 x 0.6 x 0.55 = 3.3 in one period), so the default backend `exact`
compares energies after rounding to nine decimals. The remaining deviations hinge on ties that
the machine of 1972 presumably decided by truncating hexadecimal arithmetic. An emulation of
that arithmetic (`ibm360`) is included; it fixes some of those values and breaks others.

**NetLogo.** Patch colours and `pcolor-white-since` are model state and are treated as such.
The `ask patches [ask <breed>-here ...]` idiom, which lets flying pairs move about 1.72 patches
per tick, is emulated exactly (a test checks the rate). `max-one-of` and `one-of` break ties at
random. The thresholds `(max - min) / 2` and the comparison `who <= hierarchy-divide` are kept
literally, as is the `who` convention of the code (lower `who` = more important opportunity).

**Which Fioretti & Lomi model?** The port follows the current NetLogo file, not the 2008 JASSS
version. In the current file agents never exit the organization after a decision, ability,
efficiency and difficulty are drawn uniformly from slider ranges, and the defaults are 100
agents per breed for 50,000 ticks. Published 2008 figures are therefore a qualitative, not a
numerical docking target.

**Speed.** The NetLogo port needs about 1.4 ms per tick with 100 agents per breed, roughly 70 s
for a 50,000-tick run. `--workers N` runs repetitions in parallel.

## References

Bendor, J., Moe, T. M. & Shotts, K. W. (2001). Recycling the garbage can: an assessment of the
research program. *American Political Science Review*, 95(1), 169–190.

Cohen, M. D., March, J. G. & Olsen, J. P. (1972). A garbage can model of organizational choice.
*Administrative Science Quarterly*, 17(1), 1–25.

Fioretti, G. & Lomi, A. (2008). An agent-based representation of the garbage can model of
organizational choice. *Journal of Artificial Societies and Social Simulation*, 11(1), 1.

Fioretti, G. & Lomi, A. (2010). Passing the buck in the garbage can model of organizational
choice. *Computational and Mathematical Organization Theory*, 16(2), 113–143.

Ye, J., Cao, L., Chen, D. & Ferrara, E. (2026). Stop drawing scientific claims from LLM social
simulations without robustness audits. arXiv:2605.18890.

## Licence

The NetLogo model is distributed under the GNU GPL v3; this repository keeps that licence
(GPL-3.0-or-later, see `pyproject.toml`).
