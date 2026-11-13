"""The batch script: its plan, its flags and the identity of the requests it issues.

Everything here runs with the Mock connector or stops after the dry-run plan; no test reaches a
model. The first tests pin the cache keys of the configurations that have already been run, so
that a change to prompts, scenario texts, seeds or the key itself cannot go unnoticed: with a
changed key the answers on disk would silently be asked again.
"""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from gcm.contextual.cache import request_key
from gcm.contextual.connectors import GeminiConnector
from gcm.contextual.experiment import plan_calls
from gcm.contextual.scenario import load_scenarios

ROOT = Path(__file__).resolve().parents[1]
ENV = (
    "OLLAMA_URL OLLAMA_MODEL OLLAMA_THINK UNI_API_BASE_URL UNI_API_KEY UNI_API_MODEL "
    "UNI_API_STRUCTURED GEMINI_API_KEY GEMINI_MODEL GEMINI_THINKING_LEVEL GEMINI_THINKING_BUDGET "
    "GEMINI_RPM GEMINI_BASE_URL"
).split()


@pytest.fixture(scope="module")
def rb():
    spec = importlib.util.spec_from_file_location("run_batch", ROOT / "scripts" / "run_batch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios()


@pytest.fixture
def data(tmp_path, monkeypatch):
    """An empty data directory and an environment without any connector settings.

    The working directory is moved away from the repository so that the developer's ``.env`` is
    not read.
    """
    for name in ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GCM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)
    return tmp_path / "data"


def keys_of(jobs, scenarios, identity) -> list[str]:
    return [
        request_key(identity, r.system, r.user, cfg.temperature, r.call_seed, r.schema, r.loop)
        for _, sid, cfg in jobs
        for r in plan_calls(scenarios[sid], cfg)
    ]


def digest(keys: list[str]) -> str:
    return hashlib.sha256("".join(keys).encode()).hexdigest()


# ---------------------------------------------------------------------- existing configurations
# Computed at commit 2e16e9f, before the flags below existed, for the plan of
#   run_batch.py --connector gemini/gemini-3.5-flash-lite --mode per_row --university
PINNED = {
    # thinking level: (first key, digest over all 720 keys in plan order)
    None: (
        "7f70110722f0b6d8",
        "6d014ebede72d770",
    ),
    "minimal": (
        "977cd254c43478ef",
        "3c239e538129a005",
    ),
}
PINNED_PAIRWISE = "faa52909b26cd9bd"  # the same plan in pairwise mode, 7200 keys, no thinking level
PINNED_CONFIG_HASHES = {
    "reference_hierarchical": "912e55aa6c6e",
    "reference_specialized": "6b08e9f8e72f",
    "reference_unsegmented": "36acf375c591",
}


@pytest.mark.parametrize("level", [None, "minimal"])
def test_cache_keys_of_the_default_configuration_are_pinned(rb, scenarios, level):
    connector = GeminiConnector(model="gemini-3.5-flash-lite", api_key="k", thinking_level=level)
    main = replace(rb.MAIN, mode="per_row", loops=5)
    jobs = rb.plan(["core", "det", "audit", "university"], main, rb.AUDIT, 2)
    keys = keys_of(jobs, scenarios, connector.identity())
    first, full = PINNED[level]
    assert len(keys) == 720
    assert keys[0].startswith(first)
    assert digest(keys).startswith(full)


def test_cache_keys_of_the_pairwise_plan_are_pinned(rb, scenarios):
    connector = GeminiConnector(model="gemini-3.5-flash-lite", api_key="k")
    jobs = rb.plan(["core", "det", "audit", "university"], replace(rb.MAIN, loops=5), rb.AUDIT, 2)
    keys = keys_of(jobs, scenarios, connector.identity())
    assert len(keys) == 7200 and digest(keys).startswith(PINNED_PAIRWISE)


def test_config_hashes_of_the_core_stage_are_pinned(rb):
    """The hash is part of the names of the structure files that are already tracked."""
    jobs = rb.plan(["core"], replace(rb.MAIN, mode="per_row", loops=5), rb.AUDIT, 2)
    assert {sid: cfg.config_hash for _, sid, cfg in jobs} == PINNED_CONFIG_HASHES


def test_dry_run_of_the_default_plan_prints_720_calls(rb, data, capsys):
    rb.main(["--connector", "mock", "--mode", "per_row", "--university", "--dry-run"])
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "connector: mock  mode: per_row"
    assert out.splitlines()[-1] == "total 720 calls, 720 still to ask"
    assert len(out.splitlines()) == 3 + 3 + 18 + 3 + 2
    assert not (data / "llm_cache").exists()


# ------------------------------------------------------------------------------------- --seed
def names(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir()) if directory.exists() else []


def test_seed_zero_is_the_default_and_other_seeds_give_new_requests(rb, scenarios):
    assert rb.MAIN.seed == 0
    identity = {"connector": "x", "model": "y"}
    main = replace(rb.MAIN, mode="per_row")
    zero = keys_of(rb.plan(["core"], main, rb.AUDIT, 2), scenarios, identity)
    one = keys_of(rb.plan(["core"], replace(main, seed=1), rb.AUDIT, 2), scenarios, identity)
    assert len(zero) == len(one) == 150 and not set(zero) & set(one)


def test_runs_with_different_seeds_write_to_different_files(rb, data, capsys):
    common = ["--connector", "mock", "--mode", "per_row", "--stages", "core", "--core-loops", "2"]
    rb.main(common)
    default = {d: names(data / d) for d in ("batch", "structures/batch", "llm_runs")}
    assert default["batch"] == ["summary__mock.csv"]
    assert len(default["structures/batch"]) == len(default["llm_runs"]) == 3
    assert not any("seed" in n for d in default.values() for n in d)

    rb.main([*common, "--seed", "3"])
    out = capsys.readouterr().out
    assert "connector: mock  mode: per_row  seed: 3" in out
    both = {d: names(data / d) for d in default}
    assert both["batch"] == ["summary__mock.csv", "summary__mock__seed3.csv"]
    for d in ("structures/batch", "llm_runs"):
        new = set(both[d]) - set(default[d])
        assert len(new) == 3 and all("seed3" in n for n in new)
    rows = (data / "batch" / "summary__mock__seed3.csv").read_text().splitlines()
    header = rows[0].split(",")
    assert {r.split(",")[header.index("seed")] for r in rows[1:]} == {"3"}

    rb.main([*common, "--seed", "0", "--dry-run"])  # explicit 0 = default: everything is cached
    assert capsys.readouterr().out.splitlines()[-1] == "total 60 calls, 0 still to ask"


def test_negative_seed_is_rejected(rb, data):
    with pytest.raises(SystemExit, match="negative"):
        rb.main(["--connector", "mock", "--seed", "-1", "--dry-run"])


# -------------------------------------------------------------------------------- --scenarios
def test_scenarios_restricts_the_reference_stages_only(rb, data, capsys):
    rb.main(["--connector", "mock", "--mode", "per_row", "--university", "--dry-run",
             "--scenarios", "reference_hierarchical"])
    lines = capsys.readouterr().out.splitlines()
    jobs = [line.split()[:2] for line in lines[1:-1]]
    assert len(jobs) == 1 + 1 + 6 + 3
    assert {sid for stage, sid in jobs if stage != "university"} == {"reference_hierarchical"}
    assert [sid for stage, sid in jobs if stage == "university"] == rb.UNIVERSITY
    assert lines[-1] == "total 340 calls, 340 still to ask"  # 50 + 20 + 6 * 20 + 150


def test_scenarios_keeps_the_order_and_the_requests_of_the_full_plan(rb, scenarios):
    main = replace(rb.MAIN, mode="per_row")
    stages = ["core", "det", "audit"]
    full = rb.plan(stages, main, rb.AUDIT, 2)
    assert rb.plan(stages, main, rb.AUDIT, 2, rb.REFERENCE) == full
    picked = ["reference_unsegmented", "reference_hierarchical"]
    part = rb.plan(stages, main, rb.AUDIT, 2, picked)
    assert part == [job for job in full if job[1] in picked]


def test_unknown_scenario_is_rejected(rb, data):
    with pytest.raises(SystemExit):
        rb.main(["--connector", "mock", "--dry-run", "--scenarios", "university_strong_power"])


# --------------------------------------------------------------------------- university_audit
def test_university_audit_applies_every_factor_to_the_three_variants(rb, scenarios):
    main = replace(rb.MAIN, mode="per_row")
    jobs = rb.plan(["university_audit"], main, rb.AUDIT, 2)
    assert len(jobs) == len(rb.AUDIT) * 3
    for (name, level), chunk in zip(rb.AUDIT, [jobs[i : i + 3] for i in range(0, 18, 3)], strict=True):
        assert [sid for _, sid, _ in chunk] == rb.UNIVERSITY
        for stage, sid, cfg in chunk:
            assert stage == f"university_audit:{name}={level}"
            # one factor away from the main configuration, with the side-loop count
            assert cfg == replace(main, scenario_id=sid, loops=2, **{name: level})
    # the same factors, loops and seeds as the audit of the reference scenarios
    reference = rb.plan(["audit"], main, rb.AUDIT, 2)
    strip = lambda js: [replace(cfg, scenario_id="") for _, _, cfg in js]  # noqa: E731
    assert strip(jobs) == strip(reference)


def test_university_audit_is_opt_in_and_respects_the_audit_selection(rb, data, capsys):
    rb.main(["--connector", "mock", "--mode", "per_row", "--university", "--dry-run"])
    assert "university_audit" not in capsys.readouterr().out

    rb.main(["--connector", "mock", "--mode", "per_row", "--dry-run", "--stages", "university_audit",
             "--audit", "item_order=shuffled", "--side-loops", "3"])
    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[:2] for line in lines[1:-1]] == [
        ["university_audit:item_order=shuffled", sid] for sid in rb.UNIVERSITY
    ]
    assert lines[-1] == "total 90 calls, 90 still to ask"


def test_university_audit_runs_and_is_labelled_in_the_summary(rb, data, capsys):
    rb.main(["--connector", "mock", "--mode", "per_row", "--stages", "university_audit",
             "--audit", "language=de", "wording=b"])
    rows = (data / "batch" / "summary__mock.csv").read_text().splitlines()
    header = rows[0].split(",")
    stages = [r.split(",")[header.index("stage")] for r in rows[1:]]
    assert stages == ["university_audit:language=de"] * 3 + ["university_audit:wording=b"] * 3
    assert len(names(data / "structures" / "batch")) == 6
