"""``gcm-fortran``: run the 324 situations of the paper and print the summary tables."""

from __future__ import annotations

import argparse
from pathlib import Path

from gcm.fortran import experiments


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=None, help="write per-run statistics to this CSV"
    )
    args = parser.parse_args(argv)

    results = experiments.run_all()
    print("Table 1: proportion of choices that resolve problems (this port, pooled):")
    print(experiments.table_1(results))
    print("\nTable 1: published:")
    print(experiments.TABLE_1_PUBLISHED)
    print("\nTable 2: effects of load (this port):")
    print(experiments.table_2(results))
    print("\nTable 2: published:")
    print(experiments.TABLE_2_PUBLISHED)
    print(
        f"\nMean choices not made: {results['choices_not_made'].mean():.2f} (paper: 1.0); "
        f"mean problems not solved: {results['problems_not_solved'].mean():.2f} (paper: 12.3)"
    )
    if args.out:
        results.to_csv(args.out, index=False)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
