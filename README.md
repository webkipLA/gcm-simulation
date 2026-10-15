# gcm: the Garbage Can Model in Python

Faithful Python re-implementations of the Garbage Can Model (GCM) of organizational choice,
built as the rule-based baseline for the bachelor's thesis *Simulation ausgewählter Bestandteile
des Entscheidungsprozesses im Garbage-Can-Modell mit generativen KI-/LLM-Agenten* (Leon Adel,
TH Köln).

| Package | Source it reproduces | Reference |
|---|---|---|
| `gcm.fortran` | FORTRAN program "version five", appendix of the original paper | Cohen, March & Olsen (1972), *Administrative Science Quarterly* 17(1) |
| `gcm.netlogo` | `GarbageCan_simplified17.nlogox` (NetLogo 7.0.4), Guido Fioretti's current version of the agent-based model | Fioretti & Lomi (2008, JASSS 11(1)/1; 2010, CMOT 16(2)); Fioretti (2024) |

Both ports keep every behavioural assumption of the models in a small, swappable component with a
rule-based default. The package `gcm.contextual` replaces exactly one of them, the decision
structure (who may enter which choice opportunity), by a *contextual* structure that language
models derive from a natural-language description of the organization. Everything else stays
rule-based, and the simulations never call a language model: they load an exported structure
file through the existing Protocols.

## Getting started

The project is managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-groups            # creates .venv with all dependencies
uv run marimo edit notebooks/gcm_notebook.py    # interactive notebook
uv run pytest                   # about 100 tests, under two minutes; LLM tests use a Mock connector
uv run gcm-fortran              # the 324 situations of the 1972 paper + docking tables (1 s)
uv run gcm-netlogo --ticks 5000 --repetitions 4 --workers 4   # the 12 BehaviorSpace experiments
```

`uv run marimo run notebooks/gcm_notebook.py` serves the notebook as a read-only app.

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
    structures.py    the nine pure structures D0-2, A0-2, E0-2; OrganizationalVariant (81 codes)
    allocation.py    closest-to-decision allocation rules, energy additivity rule
    arithmetic.py    exact / float64 / IBM System/360 emulation backends
    model.py         the period loop (labels of the listing cited inline)
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
    scenarios/       reference scenarios (the three pure structures in plain language) and
                     university placeholders along administrative power and problem interrelation
    representation.py  prose, role list and statute renderings; importance switch; item order
    prompts.py       system and user templates (wording, perspective, language, query mode),
                     JSON answer and schema, guard against theory terms in prompts
    connectors/      one interface; Ollama, OpenAI-compatible (university API), Gemini, Mock
    cache.py, runlog.py  disk cache keyed by the full request; raw responses as JSON Lines
    experiment.py    factor grid, call planning (count before running), the runner
    aggregate.py     yes share, valid n, Wilson interval, threshold or sampled binarization,
                     degeneracy report, agreement (kappa), distances to the references
    structure_io.py  the exported structure file (probability matrix, binary matrix, provenance)
    fortran_adapter.py   DecisionStructure.matrix(state) backed by an export (transposed here)
    netlogo_adapter.py   role x type export expanded to agents (roles onto abilities: random,
                     ranked, inverse); the *_may_enter permissions by lookup
    metrics.py       per-level metrics for both ports (styles, latencies, resolution rates)
    compare.py       baselines and contextual structures over identical situations or seeds;
                     chi-square with Cramér's V, bootstrap intervals, paired differences, Cohen's d
notebooks/gcm_notebook.py   marimo notebook: run, inspect, dock, architecture, contextual structure
tests/               matrices vs. printed arrays, Table 5 rows, docking tolerances, mechanics,
                     and the contextual pipeline end to end with the Mock connector
```

## The contextual decision structure (section 5 of the notebook)

1. A scenario (`gcm/contextual/scenarios/*.yaml`) is rendered as text in one of three formats.
2. For every participant × opportunity pair a language model is asked, several times, whether
   the participant is *permitted* to take part (eligibility only; the model never decides whether
   the participant would want to attend). The answer is a JSON object such as
   `{"reason": "...", "eligible": true}`; invalid answers are counted, never defaulted.
3. The answers become a yes share per cell with a Wilson interval, and a binary structure by
   threshold (default 0.5) or by sampling one matrix per simulation run.
4. The structure is exported to `data/structures/` and loaded by the simulations through the
   existing Protocols (`ContextualDecisionStructure` for the FORTRAN port, which needs exactly
   10 × 10; `ContextualNetLogoDecisionStructure` for the NetLogo port, which expands a small
   role × type matrix to the agents).
5. Baselines and the contextual structure are run over the same situations (FORTRAN) or seeds
   (NetLogo) and compared with the metrics of the codebase plus per-level metrics.

Connectors are configured through environment variables or a git-ignored `.env` (see
`.env.example`): `OLLAMA_URL`/`OLLAMA_MODEL`, `UNI_API_BASE_URL`/`UNI_API_KEY`/`UNI_API_MODEL`
(OpenAI-compatible), `GEMINI_API_KEY`/`GEMINI_MODEL`. Without any of them the notebook runs with
the Mock connector, which answers from the scenario's expected matrix with configurable noise.
Language models are called only when the notebook's run button is pressed; every request is
cached on disk (`data/llm_cache/`) and every raw response logged (`data/llm_runs/*.jsonl`), so a
re-run never repeats a call.

Prompts never mention the garbage can model, the organization type of the 1972 paper or the
names of the structures. In the texts of this project "organized anarchy" is that organization
type; in the NetLogo code the same words name the setting without restrictions
(`Structure.ORGANIZED_ANARCHY`). The unrestricted matrix is called *unsegmented*, as in the
paper.

```python
from gcm.contextual import load_scenarios
from gcm.contextual.aggregate import aggregate
from gcm.contextual.connectors import MockConnector, OllamaConnector
from gcm.contextual.experiment import ExperimentConfig, run_experiment
from gcm.contextual.fortran_adapter import ContextualDecisionStructure
from gcm.contextual.structure_io import StructureExport

scenario = load_scenarios()["reference_hierarchical"]
config = ExperimentConfig(scenario.id, representation="statute", language="de", loops=5)
connector = MockConnector.for_scenario(scenario, noise=0.1)   # or OllamaConnector("qwen3:8b")
result = run_experiment(scenario, config, connector)
export = StructureExport.from_estimate(aggregate(result.records, scenario), scenario)
components.decision_structure = ContextualDecisionStructure(export)   # FortranComponents
```

## Extension points (where LLM agents will plug in)

| Aspect of the GCM | FORTRAN model | NetLogo model |
|---|---|---|
| Decision structure: which participants may use which opportunities (**contextual implementation in `gcm.contextual`**) | `DecisionStructure.matrix(state)` returns matrix D (queried every period) | `DecisionStructure.participant_may_enter(...)` / `.opportunity_may_enter(...)` |
| Access structure: which problems reach which opportunities | `AccessStructure.matrix(state)` returns matrix A | `AccessStructure.problem_may_enter(...)` / `.opportunity_may_enter(...)` |
| Availability structure (solutions) | not in the original model | `AvailabilityStructure.solution_may_enter(...)` / `.opportunity_may_enter(...)` |
| Energy allocation of decision makers (optional substitution) | `DecisionMakerAllocationRule.choose(dm, state)` | random walk (no seam yet) |
| Problem allocation | `ProblemAllocationRule.choose(problem, state)` | random walk |
| Energy distribution | `EnergyDistribution.matrix(n_dm, n_periods, arith)` | uniform draw at setup |
| Decision rule | `ChoiceRule.is_made(choice, state)` | `ResolutionRule.resolves(here, model)` |
| Flights | emergent | `FlightSelector.postponement(...)` / `.buck_passing(...)` |

A substitute is any object with the listed methods and a `name`, handed to the model via
`FortranComponents` or `NetLogoComponents`:

```python
from gcm.netlogo import GarbageCanABM, NetLogoComponents, NetLogoParameters, Structure

params = NetLogoParameters(seed=1, stop_at=2000).with_structures(Structure.ORGANIZED_ANARCHY)
components = NetLogoComponents.classic(params)
components.decision_structure = MyDecisionStructure()   # implements the Protocol
results = GarbageCanABM(params, components=components).run()
print(results.share_resolutions)
```

The structure components are consulted on every allocation (FORTRAN) or every attempted move
(NetLogo). The contextual implementation therefore decides once, before the simulation, and the
components merely look the exported structure up in these methods, which keeps the LLM calls
short, few and independent, as the Exposé requires, and keeps simulation speed unchanged.

## Fidelity notes

**FORTRAN.** The listing is reproduced block by block; the labels of the original statements are
cited in the source. The entry-time cards match the orders printed in the paper. The program does
not compute decision styles; they are derived from the histories following the definitions on
p. 8 of the paper (resolution if problems are attached when the choice is made, flight if
problems had been attached earlier, oversight otherwise). Two details cannot be recovered from the
listing and are exposed as parameters: the initial requirement of a fresh choice
(`initial_choice_requirement`, read as `1.1`) and the arithmetic used to decide ties. The paper's
parameter space is full of exact ties (three light-load problems need 3 × 1.1 = 3.3, ten equal
decision makers supply 10 × 0.6 × 0.55 = 3.3 in one period), so the default backend `exact`
compares energies after rounding to nine decimals, which realises the stated "equals or exceeds"
semantics. With it the port reproduces nine of the twelve rows of Table 5 to within the paper's
rounding, the aggregate means (1.05 choices not made vs. 1.0; 12.0 problems not solved vs. 12.3)
and Table 2 within a few percent; the remaining Table 1/5 cells hinge on ties that the 1972 IBM
System/360 decided by truncating hexadecimal arithmetic. An emulation of that arithmetic (`ibm360`)
is included as an experiment; it fixes some of those rows and breaks others, which is the expected
signature of a machine dependence.

**NetLogo.** Patch colours and `pcolor-white-since` are model state (flight conditions, the
monitor and `free-spot` read them) and are treated as such. The `ask patches [ask <breed>-here …]`
idiom, which lets flying pairs move about e − 1 ≈ 1.72 patches per tick because agents are asked
again on not-yet-visited patches, is emulated exactly (random patch order with re-queuing; a test
checks the rate). `max-one-of` and `one-of` break ties at random. The thresholds `(max − min) / 2`
and the comparison `who <= hierarchy-divide` are kept literally, as is the `who` convention of the
code (lower `who` = more important opportunity; the comment in `setup` says the opposite). The
"Things to notice" of the model's info tab (most decisions by oversight; flights raise the share of
resolutions; anarchies out-resolve hierarchies; incompetent hierarchies are at least as efficient
as competent ones) are reproduced in short runs, see `tests/test_netlogo.py`.

**Which Fioretti & Lomi model?** The port follows the *current* NetLogo file
(`GarbageCan_simplified17`, updated to NetLogo 7.0.4), as requested. It differs from the 2008
JASSS version cited in the Exposé (100 participants, 200 opportunities, 100 solutions, 400
problems, 200 steps): in the current file agents never exit the organization after a decision,
ability/efficiency/difficulty are drawn uniformly from slider ranges, and the interface defaults
are 100 agents per breed for 50 000 ticks. The 2008 population sizes can be set through
`NetLogoParameters`, but the exit mechanics of the 2008 code are not part of this model (Fioretti
notes the difference himself in the info tab), so published 2008 figures are a qualitative rather
than numerical docking target.

**Speed.** The NetLogo port runs at about 1.4 ms per tick with 100 agents per breed in pure
Python, i.e. roughly 70 s for a full 50 000-tick BehaviorSpace run. `gcm-netlogo --workers N`
parallelises repetitions across processes.

## References

Cohen, M. D., March, J. G. & Olsen, J. P. (1972). A garbage can model of organizational choice.
*Administrative Science Quarterly*, 17(1), 1–25.

Fioretti, G. & Lomi, A. (2008). An agent-based representation of the garbage can model of
organizational choice. *Journal of Artificial Societies and Social Simulation*, 11(1), 1.

Fioretti, G. & Lomi, A. (2010). Passing the buck in the garbage can model of organizational
choice. *Computational and Mathematical Organization Theory*, 16(2), 113–143.

Ye, J., Cao, L., Chen, D. & Ferrara, E. (2026). Stop drawing scientific claims from LLM social
simulations without robustness audits. arXiv:2605.18890.

Bendor, J., Moe, T. M. & Shotts, K. W. (2001). Recycling the garbage can: an assessment of the
research program. *American Political Science Review*, 95(1), 169–190.

The NetLogo model is distributed under the GNU GPL v3; this port keeps that licence.
