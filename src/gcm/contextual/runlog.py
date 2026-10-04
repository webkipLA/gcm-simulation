"""Raw responses as JSON Lines.

One file per experiment configuration and connector. A file holds one record per call with
everything needed to reproduce and audit it: connector, model id, template hash, scenario,
representation, all factors, seed, loop, timestamp, both messages, the raw text and the parsed
answer. The file is rewritten as a whole when a configuration is run again; records that come
from the cache keep the timestamp of the original call.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path


def write_jsonl(path: str | Path, records: Iterable[dict]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)
    return path


def read_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


__all__ = ["read_jsonl", "write_jsonl"]
