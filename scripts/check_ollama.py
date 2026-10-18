"""Quick speed check of the local Ollama model: one real eligibility question, with and without
thinking, so the effect of OLLAMA_THINK can be seen before a long batch run.

  uv run python scripts/check_ollama.py
  uv run python scripts/check_ollama.py --repeat 3

Prints wall time, generated tokens and whether the model returned a thinking trace. Answers are
not cached and not logged.
"""

from __future__ import annotations

import argparse
import os
import time

import httpx

from gcm.contextual import prompts
from gcm.contextual.experiment import ExperimentConfig, plan_calls
from gcm.contextual.paths import load_env
from gcm.contextual.scenario import load_scenarios


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--mode", choices=list(prompts.MODES), default="pairwise")
    args = ap.parse_args()

    load_env()
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "").split(",")[0].strip()
    if not model:
        raise SystemExit("OLLAMA_MODEL is not set (.env)")
    scenario = load_scenarios()["reference_hierarchical"]
    request = plan_calls(scenario, ExperimentConfig(scenario.id, mode=args.mode, loops=1))[3]
    print(f"model {model} at {url}, mode {args.mode}, one question for {request.row_id}")

    with httpx.Client(timeout=600) as client:
        try:
            ps = client.get(f"{url}/api/ps").json()
            for m in ps.get("models", []):
                total, vram = m.get("size", 0), m.get("size_vram", 0)
                where = "GPU" if total and vram >= total else (f"{vram / total:.0%} GPU" if total else "?")
                print(f"loaded: {m.get('name')} ({total / 1e9:.1f} GB, {where})")
        except Exception as exc:  # noqa: BLE001
            print(f"/api/ps not available: {exc}")
        for think in (None, False):
            for i in range(args.repeat):
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": request.system},
                        {"role": "user", "content": request.user},
                    ],
                    "stream": False,
                    "format": request.schema,
                    "options": {"temperature": 0.7, "seed": 1000 + i},
                }
                if think is not None:
                    payload["think"] = think
                t = time.time()
                data = client.post(f"{url}/api/chat", json=payload).json()
                wall = time.time() - t
                msg = data.get("message") or {}
                thinking = msg.get("thinking") or ""
                content = msg.get("content") or ""
                print(
                    f"think={'unset' if think is None else think!s:5}  {wall:6.1f} s  "
                    f"tokens out {data.get('eval_count', '?'):>5}  thinking trace {len(thinking):>6} chars  "
                    f"answer {content[:90]!r}"
                )


if __name__ == "__main__":
    main()
