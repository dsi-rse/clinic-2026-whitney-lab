r"""Compare an experiment's arms: original run, control repeats, and edit arms.

    python scripts/compare_arms.py \
        --controls runs/2026-10-13_issue8_s1_control runs/2026-10-13_issue8_s2_control \
        --arm flip=runs/2026-10-13_issue8_flip --arm reword=runs/2026-10-13_issue8_reword

Run folders are relative to the workspace. Writes `arm_comparison.csv` (edited
patients) and `control_noise.csv` (every control patient) to the issue 8
analysis folder and prints both. Only IDs, labels, and counts are written.
"""

import argparse
from pathlib import Path

import pandas as pd

from oncotrace_bench.arm_comparison import compare_arms, noise_rows
from oncotrace_bench.records import ANALYSIS_DIR, DEFAULT_RUN, WORKSPACE


def main() -> None:
    """Build and print the comparison tables."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--original", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--controls", type=Path, nargs="+", required=True)
    parser.add_argument("--arm", action="append", default=[], help="NAME=RUN_DIR")
    parser.add_argument("--inputs", type=Path, default=ANALYSIS_DIR / "inputs")
    parser.add_argument("--out-dir", type=Path, default=ANALYSIS_DIR)
    args = parser.parse_args()

    controls = [WORKSPACE / path for path in args.controls]
    arms = {}
    for item in args.arm:
        name, _, path = item.partition("=")
        arms[name] = WORKSPACE / path

    noise = pd.DataFrame(noise_rows(args.original, controls))
    noise.to_csv(args.out_dir / "control_noise.csv", index=False)
    print(noise.to_string(index=False))
    print(
        f"\npatients with more than one distinct answer: "
        f"{(noise['distinct_answers'] > 1).sum()} of {len(noise)}\n"
    )

    if arms:
        table = pd.DataFrame(compare_arms(args.original, controls, arms, args.inputs))
        table.to_csv(args.out_dir / "arm_comparison.csv", index=False)
        print(table.to_string(index=False))
        for name in arms:
            hits = table[f"{name}_as_expected"].sum()
            print(f"{name}: {hits} of {len(table)} patients answered as expected")


if __name__ == "__main__":
    main()
