# gcm: the Garbage Can Model in Python, with a decision structure derived by language models

Code and results for the bachelor's thesis *Simulation ausgewählter Bestandteile des
Entscheidungsprozesses im Garbage-Can-Modell mit generativen KI-/LLM-Agenten* (Leon Adel,
TH Köln, 2026).

The repository contains three things:

| Package | What it is | Reference |
|---|---|---|
| `gcm.fortran` | Python port of the FORTRAN program "version five" printed in the appendix of the original paper | Cohen, March & Olsen (1972) |
| `gcm.netlogo` | Python port of Guido Fioretti's current NetLogo model (`GarbageCan_simplified17`, NetLogo 7.0.4) | Fioretti & Lomi (2008, 2010) |
| `gcm.contextual` | The LLM component: a language model reads a description of an organization and decides who may take part in which choice opportunity. The result replaces exactly one rule-based part of the ports, the decision structure. | thesis, chapter 3.3 |

The simulations themselves never call a language model. They load a stored structure file, so
every simulation result can be recomputed without an API key.

The three research questions of the thesis map onto the code like this:

- **FF1** (do the two ports reproduce the published models?): `scripts/run_docking.py`,
  `scripts/netlogo_original.py`
- **FF2** (how faithfully does a language model turn a described structure into a matrix?):
  `scripts/run_batch.py`, then `scripts/analyse_results.py`
- **FF3** (what does the substituted structure do to the model's behaviour, and how robust is
  that?): `scripts/analyse_results.py`, `scripts/run_netlogo_llm.py`

## Setup

Requirements: [uv](https://docs.astral.sh/uv/) and nothing else. uv installs Python 3.11 and all
dependencies into a local `.venv`.

```bash
git clone https://github.com/webkipLA/gcm-simulation
cd gcm-simulation
uv sync --all-groups
uv run pytest -q          # 191 tests, two to four minutes, no network and no API key needed
```

All commands below are run from the repository root. On Windows they work unchanged in
PowerShell.

## What can be reproduced, and what it needs

| Level | What | Needs | Time |
|---|---|---|---|
| 1 | Tests, FORTRAN port, docking of the FORTRAN port against the 1972 paper, comparison of the initial requirement | nothing beyond the setup | seconds |
| 2 | Docking of the NetLogo port (12 experiments, 30 seeds, 50,000 ticks) | CPU time | about two hours (7,415 s in the stored report) |
| 3 | Every table and figure of chapter 4 from the stored LLM answers | the raw answers in `data/llm_runs/` | minutes |
| 4 | Transfer check in the NetLogo port | 90 new model calls (API key), then CPU time | 100 runs of about 70 s each |
| 5 | Comparison of the port with the original NetLogo model | a NetLogo 7.0.4 installation | 360 NetLogo runs |
| 6 | Asking the language models again | API key for Gemini, or a local Ollama | see below |

Level 6 does not reproduce the thesis numbers exactly. The models answer at temperature 0.7,
the hosted models can change on the provider's side, and a new call is a new sample. What is
reproducible exactly is everything computed *from* the stored answers and structures (levels 1
to 3). The structures used in the thesis are in `data/structures/`, each with a `provenance`
block naming model, settings, seed and date.

## Step by step

### 1. The FORTRAN port and its docking (FF1)

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

### 2. The original NetLogo model against the port (FF1)

Needs NetLogo 7.0.4. `data/netlogo_original/GarbageCan_fioretti.nlogox` is the model file the
port follows. `GarbageCan_simplified17_headless.nlogox` is a copy with the same
model code whose BehaviorSpace experiments are set to 30 repetitions and to the same 13
reported quantities for every experiment.

```bash
uv run python scripts/netlogo_original.py prepare --model data/netlogo_original/GarbageCan_fioretti.nlogox
NETLOGO=/path/to/NetLogo_Console ./data/netlogo_original/run_original.sh     # Windows: .\data\netlogo_original\run_original.ps1
uv run python scripts/netlogo_original.py compare
```

Result: `data/netlogo_original/report.md`. BehaviorSpace sets no seeds, so the comparison is
between distributions, not between individual runs.

### 3. Structures from language models (FF2)

Configure the models in `.env` (copy `.env.example`). `--dry-run` prints the plan and how many
calls are already answered, without calling a model:

```bash
uv run python scripts/run_batch.py --connector gemini/gemini-3.5-flash-lite --mode per_row --university --dry-run
```

The runs of the thesis, all with `--mode per_row` (one call per participant, ten per loop):

| Model and setting | Command (after `uv run python scripts/run_batch.py --mode per_row`) | Calls |
|---|---|---|
| Main model gemini-3.5-flash-lite, thinking level `minimal` | `--connector gemini/gemini-3.5-flash-lite --university` | 720 |
| same, university scenario without the participation statement | `--connector gemini/gemini-3.5-flash-lite --stages university_np` | 150 |
| same, university scenario with shuffled item order | `--connector gemini/gemini-3.5-flash-lite --stages university_audit --audit item_order=shuffled` | 60 |
| Main model with thinking level `low`, university scenario | `--connector gemini/gemini-3.5-flash-lite --stages university --thinking-level low` | 150 |
| gemini-4-argon, thinking level `low` (the model rejects `minimal`) | `--connector gemini/gemini-4-argon --stages core university --thinking-level low` | 300 |
| qwen3:4b via Ollama, thinking off | `--connector ollama/qwen3:4b --stages core det` | 210 |
| same, audit | `--connector ollama/qwen3:4b --stages audit` | 360 |
| same, three audit factors with five loops for the hierarchical form | `--connector ollama/qwen3:4b --stages audit --scenarios reference_hierarchical --audit wording=b item_order=shuffled perspective=persona --side-loops 5` | 90 more |

A supplementary run of qwen3:8b (hierarchical reference scenario, 500 calls) used the pairwise
mode from the notebook. The main-model runs used `GEMINI_THINKING_LEVEL=minimal` and the qwen
runs `OLLAMA_THINK=false` in `.env`.

Every answer is written to the disk cache at once (`data/llm_cache/`), so a run can be stopped
and restarted and nothing is asked twice. Output: raw answers in `data/llm_runs/*.jsonl`, one
structure per configuration in `data/structures/batch/`, one summary row per configuration in
`data/batch/summary__<connector>.csv`. `uv run python scripts/run_batch.py --help` documents all
stages and flags.

To try the pipeline without any model: `uv run python scripts/run_batch.py --connector mock`.

### 4. Analysis of chapter 4 (FF2 and FF3)

```bash
uv run python scripts/analyse_results.py                      # everything, null model with 200 draws
uv run python scripts/analyse_results.py --null 0             # without the null model (fast)
uv run python scripts/analyse_results.py --arithmetic ibm360  # all FORTRAN comparisons with the second arithmetic
```

Reads `data/llm_runs/`, `data/docking/` and `data/netlogo_llm/` and writes tables, figures and
`report.md` to `data/analysis/` (to `data/analysis__ibm360/` for the second arithmetic, with
`arithmetic_comparison.md` setting the two side by side).

### 5. Transfer check in the NetLogo port (FF3)

```bash
uv run python scripts/run_netlogo_llm.py llm --connector gemini/gemini-3.5-flash-lite
uv run python scripts/run_netlogo_llm.py sim --connector gemini/gemini-3.5-flash-lite --ticks 50000 --seeds 10 --workers 6
uv run python scripts/run_netlogo_llm.py sim --connector gemini/gemini-3.5-flash-lite --ticks 50000 --seeds 10 --workers 6 --exclusion-controls
```

The `llm` step asks about the role scenario (90 calls) and stores the answers in the local
cache. The `sim` step needs these answers and a configured connector name, but makes no model
call. The cache of the thesis run is not part of the repository. Its three structures are in
`data/structures/roles/` and its simulation runs in `data/netlogo_llm/runs_*.csv`.
Result: `data/netlogo_llm/report_ranked_50000t_10s.md` and, with the control conditions,
`report_ranked_50000t_10s_controls.md`.

## Where the results of the thesis are

These files are part of the repository and can be read without running anything.

The repository stores only what cannot be produced again cheaply: the raw answers of the
language models (`data/llm_runs/`), the structures derived from them, the runs of the NetLogo
port and of the original NetLogo model, and the reports. All other tables are written again by
the scripts within minutes and are therefore not tracked.

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
| The decision structures used in the simulations | `data/structures/batch/`, `data/structures/roles/` | `run_batch.py`, `run_netlogo_llm.py` |

The reports use the German terms of the thesis in their headings. The code and its
documentation are in English. The reports also contain statistics that the thesis does not
report (pooled chi-square tests, Cramér's V, Cohen's d).

## Layout

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
  contextual/
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
scripts/             the five scripts described above, plus check_ollama.py (speed check of a
                     local model)
notebooks/gcm_notebook.py   marimo notebook: run, inspect, dock, architecture, LLM component
tests/               matrices against the printed arrays, Table 5 rows, docking tolerances,
                     mechanics, and the LLM pipeline end to end with the Mock connector
data/                reference values, stored structures and the reports listed above
```

The notebook is optional: `uv run marimo edit notebooks/gcm_notebook.py` opens it for editing,
`uv run marimo run notebooks/gcm_notebook.py` serves it read-only.

## How the LLM component works

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

## Configuration

Connectors read environment variables or a git-ignored `.env` (see `.env.example`):
`OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_THINK`; `GEMINI_API_KEY`, `GEMINI_MODEL`,
`GEMINI_THINKING_LEVEL`, `GEMINI_RPM`; `UNI_API_BASE_URL`, `UNI_API_KEY`, `UNI_API_MODEL` for any
OpenAI-compatible endpoint. Model, thinking setting, temperature, seed and the full prompt are
part of every cache key, so answers obtained with different settings are never mixed.

## Extension points

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

## Fidelity notes

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
