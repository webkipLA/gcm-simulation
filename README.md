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
rule-based default. **No LLM-based component is implemented yet.** The seams exist so that the
substitutions planned in the Exposé (decision/access structure, optionally energy allocation) can
be added later without touching the simulation cores.

## Getting started

The project is managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-groups            # creates .venv with all dependencies
uv run marimo edit notebooks/gcm_notebook.py    # interactive notebook
uv run pytest                   # 30 tests, about one minute
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
notebooks/gcm_notebook.py   marimo notebook: run, inspect, dock, and the architecture overview
tests/               matrices vs. printed arrays, Table 5 rows, docking tolerances, mechanics
```

## Extension points (where LLM agents will plug in)

| Aspect of the GCM | FORTRAN model | NetLogo model |
|---|---|---|
| Decision structure: which participants may use which opportunities | `DecisionStructure.matrix(state)` returns matrix D (queried every period) | `DecisionStructure.participant_may_enter(...)` / `.opportunity_may_enter(...)` |
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
(NetLogo). An LLM-backed implementation should therefore decide at a coarser granularity (per
participant and period, or per participant and hierarchy level), cache the answers and merely look
them up in these methods. This also keeps the LLM calls short, few and independent, as the Exposé
requires.

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

Bendor, J., Moe, T. M. & Shotts, K. W. (2001). Recycling the garbage can: an assessment of the
research program. *American Political Science Review*, 95(1), 169–190.

The NetLogo model is distributed under the GNU GPL v3; this port keeps that licence.
