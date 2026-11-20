"""Write the two rosters the issue #42 runs use.

- `rosters/roster_compare.csv`: the 66 annotated patients, plus every patient the
  extent-wording scan found that is not among them (the patients a rule for
  TCGA-A5-A0GJ's wording could touch).
- `rosters/roster_a0gr.csv`: TCGA-A5-A0GR alone, for the temperature-1.0 repeats.

Run from the repo root, after `scan_extent_wording.py`:

    PYTHONPATH=src python experiments/issue42_depth_rules/make_rosters.py \
        --scan experiments/issue42_depth_rules/results/<scan folder>
"""

import argparse
from pathlib import Path

import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
ANNOTATED = REPO_ROOT / "experiments/endometrial_baseline_full/roster_annotated66.csv"
A0GR = "TCGA-A5-A0GR"


def main() -> None:
    """Write both rosters into the experiment's rosters/ folder."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scan", type=Path, required=True, help="scan results folder")
    parser.add_argument("--annotated", type=Path, default=ANNOTATED)
    parser.add_argument("--out", type=Path, default=EXPERIMENT_DIR / "rosters")
    args = parser.parse_args()

    annotated = pd.read_csv(args.annotated)["unit"].tolist()
    touched = pd.read_csv(args.scan / "extent_patients.csv")["patient"].tolist()
    extra = sorted(set(touched) - set(annotated))

    args.out.mkdir(exist_ok=True)
    pd.DataFrame({"unit": annotated + extra}).to_csv(
        args.out / "roster_compare.csv", index=False
    )
    pd.DataFrame({"unit": [A0GR]}).to_csv(args.out / "roster_a0gr.csv", index=False)
    print(
        f"roster_compare.csv: {len(annotated)} annotated + {len(extra)} from the scan"
    )


if __name__ == "__main__":
    main()
