"""``gcm-netlogo``: run the BehaviorSpace experiments of the NetLogo model."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from gcm.netlogo import experiments
from gcm.netlogo.parameters import behavior_space_experiments


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ticks", type=int, default=5000, help="ticks per run (BehaviorSpace: 50000)"
    )
    parser.add_argument("--repetitions", type=int, default=3, help="runs (seeds) per experiment")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument(
        "--only", nargs="*", default=None, help="experiment names to run (default: all 12)"
    )
    parser.add_argument("--out", type=Path, default=None, help="write per-run results to this CSV")
    args = parser.parse_args(argv)

    exps = behavior_space_experiments()
    if args.only:
        exps = {k: v for k, v in exps.items() if k in set(args.only)}
    df = experiments.run_experiments(
        exps, repetitions=args.repetitions, ticks=args.ticks, workers=args.workers
    )
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print(experiments.summarise_experiments(df).to_string())
    if args.out:
        df.to_csv(args.out, index=False)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
