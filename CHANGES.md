# Changes

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
