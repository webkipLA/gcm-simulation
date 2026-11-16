# Changes

## 2026-11-16: runs without a language model

Four additions, each opt-in. Without the new options every script writes what it wrote before.

| Script and option | What it does | Output |
|---|---|---|
| `run_docking.py --initial-requirement 1.1 0 1.0` | Runs the 324 situations with other initial energy requirements of a choice (XERC, 1.1 in the listing) and compares them. | `fortran_configurations.csv`, `fortran_configurations_changed_values.csv` and a section in `docking_report.md`. Use `--out`, because the report in `data/docking` is rewritten on every start. |
| `analyse_results.py --arithmetic ibm360` | Repeats every FORTRAN condition of the analysis with another arithmetic backend. | `data/analysis__ibm360/` with `arithmetic_comparison.md`; `data/analysis` is not touched. |
| `run_netlogo_llm.py sim --exclusion-controls` | Adds, for every LLM structure that shuts whole groups out, the expected form with the same groups shut out. | Files with the suffix `_controls` in `data/netlogo_llm`. |
| `netlogo_original.py prepare` / `compare` | Prepares the original NetLogo model for a headless run and compares its result tables with the port. Needs a NetLogo installation. | `data/netlogo_original/` |

`analyse_results.py` also analyses further university conditions when their run logs exist (without
the participation statement, the main model with thinking level low, gemini-4-argon): section
"FF3: Hochschulszenario, weitere Bedingungen im FORTRAN-Port", files `ff3_university_extra_*` and
the figures `abb_4_6` to `abb_4_8`.

## 2026-11-13: extensions of the batch run (scripts/run_batch.py)

Nothing changes for the configurations that have already been run. Prompt texts, scenario texts,
seed derivation and cache keys are the same; tests/test_run_batch.py pins the keys of the plan of
`--connector gemini/gemini-3.5-flash-lite --mode per_row --university` (720 calls), with and
without a thinking level, and of the same plan in pairwise mode. All new behaviour is opt-in,
with one exception that is marked below.

### New flags and stages

| Flag or stage | Default | What it does |
|---|---|---|
| `--seed N` | `0` (the runs so far) | Base seed from which the seed of every call and the shuffled item orders are derived. Any other seed writes to `..__seed<N>` files (summary, structures, logs). |
| `--scenarios NAME [NAME ...]` | all three reference scenarios | Restricts the stages core, det and audit, e.g. `--scenarios reference_hierarchical`. |
| `--stages university_audit` | not run | The audit factors, one at a time, on the three university variants, with `--side-loops`. Respects `--audit FACTOR=LEVEL`. |
| `--stages university_np` | not run | The three university variants without their participation statement (`university_*_no_participation`), with `--core-loops`. Removed and borderline sentences: `docs/university_no_participation_diff.md`. |
| `--thinking-level LEVEL` | not set: `GEMINI_THINKING_LEVEL` / `GEMINI_THINKING_BUDGET` of `.env` | Gemini only. `minimal`, `low`, `medium`, `high` or `default` (send no thinking setting). Takes precedence over `.env`. Writes to `..__think-<LEVEL>` files. |
| `--ollama-think true\|false` | not set: `OLLAMA_THINK` of `.env` | Ollama only. Takes precedence over `.env`. Writes to `..__think-<value>` files. |
| `--no-fail-fast` | off, so the script now stops early | See "Changed default" below. |
| `--connector uni/<model>` | | Short form of `university/<model>`, which already existed: the OpenAI-compatible endpoint of `UNI_API_BASE_URL`, `UNI_API_KEY`, `UNI_API_MODEL`, `UNI_API_STRUCTURED`. |

One example per flag is in `uv run python scripts/run_batch.py --help`.

### Changed default: stop at the first refused request

A response with HTTP 4xx other than 408, 409, 425 and 429 means that the request itself is wrong
(a thinking level the model does not accept, a wrong key, an unknown model). The script now stops
after the first such call and prints the server message in full. Before, every call of the
configuration was sent first. Rate limits (429), server errors (5xx) and timeouts are retried and
counted as before. `--no-fail-fast` restores the old behaviour. The library default is unchanged:
`run_experiment(..., stop_on_config_error=False)`, so the notebook behaves as before.

### Cache identity

- The Gemini thinking level and thinking budget and the Ollama think setting were already part of
  the connector identity and therefore of every cache key. No change; tests now state it.
- The model name of the university connector is part of its identity, together with the base URL
  and the output format (`UNI_API_STRUCTURED`).

### Summary (data/batch/summary__<connector>.csv)

The existing columns keep their names and their order. Appended: `model` (as requested;
`model_ids` stays the id the provider reports), `base_seed`, `thinking`, `query_mode`,
`git_commit` (short hash, `+dirty` with uncommitted changes), `run_date` (day the row was
written), `first_call`, `last_call` (time of the answers; cached answers keep theirs) and
`structure_file`.

Unchanged and worth knowing: the summary is rewritten on every start with the rows of the stages
of that start only. A run of `--stages university_np` with the main connector therefore replaces
the summary of the earlier stages. The answers stay in the cache; a start with all stages rebuilds
the full summary without a model call. Copy the file first if you want to keep it as it is.

### Exported structures (data/structures/batch/*.json)

File names and matrices of existing configurations are unchanged. The `provenance` of each file
now also holds `stage`, `connector` (identity), `factors` (with seed, mode, loops, temperature),
`config_hash`, `template_hash` and `git_commit`. Select structures by these fields or through
`structure_file` of the summary, not by the start of the file name: `university-strong-power-*`
also matches the no_participation variant, the university audit and other seeds.

### Analysis (scripts/analyse_results.py)

The script reads the run logs and selects runs by model, scenario and factors. The scenario id is
compared exactly, and every audit run differs from the main configuration in one factor, so the
stages university_np and university_audit could not be confused with the university stage. Two
things did need a change:

- The selection did not look at the seed. With a second seed for the same configuration the script
  stopped with "2 matching run logs". It now takes base seed 0 for the comparisons and figures.
- `ff2_configs.csv` had no column for the seed or the thinking setting, so rows of two seeds looked
  alike. `seed` and `thinking` are appended as the last columns. Token counts of OpenAI-compatible
  servers (the university API) are now read as well.

Not solvable from the factors: the same model with the same configuration and two thinking
settings. The script then stops and names both log files instead of choosing one. The numbers for
the existing run logs do not change.

### Scenario files

A variant may be declared as `derived_from: <variant>` with `omit_statements: [n, ...]`. It is a
copy of that variant without the listed statements and cannot set anything else.

### Dry run of the two new stages

```
$ uv run python scripts/run_batch.py --connector mock --mode per_row --stages university_audit university_np --dry-run
connector: mock  mode: per_row
  university_audit:representation=role_list university_strong_power         20 calls,    20 missing
  university_audit:representation=role_list university_moderate_power       20 calls,    20 missing
  university_audit:representation=role_list university_weak_power           20 calls,    20 missing
  university_audit:representation=statute university_strong_power         20 calls,    20 missing
  university_audit:representation=statute university_moderate_power       20 calls,    20 missing
  university_audit:representation=statute university_weak_power           20 calls,    20 missing
  university_audit:perspective=persona university_strong_power         20 calls,    20 missing
  university_audit:perspective=persona university_moderate_power       20 calls,    20 missing
  university_audit:perspective=persona university_weak_power           20 calls,    20 missing
  university_audit:wording=b   university_strong_power         20 calls,    20 missing
  university_audit:wording=b   university_moderate_power       20 calls,    20 missing
  university_audit:wording=b   university_weak_power           20 calls,    20 missing
  university_audit:item_order=shuffled university_strong_power         20 calls,    20 missing
  university_audit:item_order=shuffled university_moderate_power       20 calls,    20 missing
  university_audit:item_order=shuffled university_weak_power           20 calls,    20 missing
  university_audit:language=de university_strong_power         20 calls,    20 missing
  university_audit:language=de university_moderate_power       20 calls,    20 missing
  university_audit:language=de university_weak_power           20 calls,    20 missing
  university_np                university_strong_power_no_participation    50 calls,    50 missing
  university_np                university_moderate_power_no_participation    50 calls,    50 missing
  university_np                university_weak_power_no_participation    50 calls,    50 missing
total 510 calls, 510 still to ask
```
