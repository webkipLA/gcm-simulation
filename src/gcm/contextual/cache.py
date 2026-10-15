"""Disk cache of LLM responses, keyed by the full request.

The key is the SHA-256 of everything that determines an answer: the connector identity (name,
model, endpoint), both messages, temperature, seed, schema and the loop index. The loop index is
part of the key so that repeated questions are distinct samples and not one cached answer.
Re-running an experiment therefore never repeats a call that has already been answered.

Only answers of the model are cached, valid or not. Failed requests (timeouts, server errors)
are not cached and are tried again on the next run.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path


def request_key(
    identity: dict,
    system: str,
    user: str,
    temperature: float,
    seed: int | None,
    schema: dict | None,
    loop: int,
) -> str:
    blob = json.dumps(
        {
            "identity": identity,
            "system": system,
            "user": user,
            "temperature": float(temperature),
            "seed": seed,
            "schema": schema,
            "loop": loop,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class DiskCache:
    """One small JSON file per request under ``directory/<first two hex digits>/``."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.json"

    def __contains__(self, key: str) -> bool:
        return self._path(key).exists()

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def put(self, key: str, value: dict) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(value, fh, ensure_ascii=False)
            os.replace(tmp, path)  # atomic: concurrent readers see the old or the new file
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def __len__(self) -> int:
        return sum(1 for _ in self.directory.glob("*/*.json")) if self.directory.exists() else 0


__all__ = ["DiskCache", "request_key"]
