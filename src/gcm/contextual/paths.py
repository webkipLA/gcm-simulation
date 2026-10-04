"""Where the pipeline keeps its files, and how configuration reaches it.

Everything is rooted at the project directory (the nearest parent of the working directory that
holds a ``pyproject.toml``), unless ``GCM_DATA_DIR`` points elsewhere:

``data/llm_cache/``   disk cache of LLM responses (git-ignored)
``data/llm_runs/``    raw responses as JSONL, one file per experiment configuration (git-ignored)
``data/structures/``  exported structures loaded by the simulations (tracked)

Secrets and endpoints come from environment variables or from a git-ignored ``.env`` file in the
project directory; see ``.env.example``.
"""

from __future__ import annotations

import os
from pathlib import Path


def project_root(start: str | Path | None = None) -> Path:
    here = Path(start) if start is not None else Path.cwd()
    for candidate in (here, *here.resolve().parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return here


def data_dir() -> Path:
    override = os.environ.get("GCM_DATA_DIR")
    return Path(override) if override else project_root() / "data"


def cache_dir() -> Path:
    return data_dir() / "llm_cache"


def runs_dir() -> Path:
    return data_dir() / "llm_runs"


def structures_dir() -> Path:
    return data_dir() / "structures"


def load_env(path: str | Path | None = None, *, override: bool = False) -> dict[str, str]:
    """Read ``KEY=VALUE`` lines of a ``.env`` file into ``os.environ``.

    Existing environment variables win unless ``override`` is set. Returns the values that were
    read. A missing file is not an error.
    """
    path = Path(path) if path is not None else project_root() / ".env"
    read: dict[str, str] = {}
    if not path.exists():
        return read
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        read[key] = value
        if override or key not in os.environ:
            os.environ[key] = value
    return read


__all__ = ["cache_dir", "data_dir", "load_env", "project_root", "runs_dir", "structures_dir"]
