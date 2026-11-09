"""Completion and cost of one or more OncoTrace runs, side by side.

Each run is a folder that holds units/<patient>.json. The script writes counts,
patient IDs and OncoTrace's own reason codes. No report text is written.
A patient with no answer counts as not answered.

Use --patients to restrict every run to the same patients (for example the 50
annotated ones), so runs made on different cohorts can be compared fairly.

Example:
    python experiments/endometrial_baseline_full/summarize_runs.py \
        --run new=/path/to/baseline/rep1 --run issue9=/path/to/issue9_run \
        --patients experiments/endometrial_baseline_full/roster_annotated50.csv \
        --out experiments/endometrial_baseline_full/results/some_label
"""

import argparse
import csv
from pathlib import Path

from compare_modes import (
    SUMMARY_HEADER,
    answer,
    cut_offs,
    load_run,
    no_answer_reason,
    refusals,
    summary_rows,
    write_csv,
)


def read_patients(path: Path) -> set[str]:
    """The patients named in the `unit` column of a roster CSV."""
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["unit"] for row in csv.DictReader(handle)}


def main() -> None:
    """Read the runs, write the tables."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        metavar="NAME=FOLDER",
        help="a run to include; repeat for several runs",
    )
    parser.add_argument(
        "--patients",
        type=Path,
        help="CSV (column unit); keep only these patients in every run",
    )
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    keep = read_patients(arguments.patients) if arguments.patients else None
    runs = {}
    for item in arguments.run:
        name, _, folder = item.partition("=")
        records = load_run(Path(folder))
        runs[name] = {
            patient: record
            for patient, record in records.items()
            if keep is None or patient in keep
        }

    arguments.out.mkdir(parents=True, exist_ok=True)
    write_csv(
        arguments.out / "completion_and_cost.csv", SUMMARY_HEADER, summary_rows(runs)
    )
    write_csv(
        arguments.out / "no_answer_patients.csv",
        ["run", "patient", "reason", "calls", "rejected_submissions", "cut_off_replies"],
        [
            [name, patient, no_answer_reason(record), record["model_calls"],
             len(refusals(record)), cut_offs(record)]
            for name, run in runs.items()
            for patient, record in run.items()
            if answer(record) is None
        ],
    )  # fmt: skip
    print(
        f"wrote {arguments.out}: " + ", ".join(f"{n}={len(r)}" for n, r in runs.items())
    )


if __name__ == "__main__":
    main()
