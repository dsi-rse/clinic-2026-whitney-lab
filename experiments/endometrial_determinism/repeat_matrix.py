"""Repeat matrix: how often does each patient get the same outcome across repeats?

A group is one run folder that holds rep1, rep2, ... For each group it writes, per
patient, the outcome in each repeat and a stability summary. Outcome is
'invasion/depth' or NO_ANSWER. No report text is written.

Example:
    python experiments/endometrial_determinism/repeat_matrix.py \
        --group old_f99cefd_10x10=/path/to/run_folder_10x10 \
        --group new_0b6f404_10x20=/path/to/run_folder_10x20 \
        --patients-csv experiments/endometrial_determinism/roster_followup10.csv \
        --out experiments/endometrial_determinism/results/repeat_matrix_followup10
"""

import argparse
import csv
import json
import os
import statistics
from collections import Counter
from pathlib import Path

from oncotrace_bench.provenance import build

REPO_ROOT = Path(__file__).resolve().parents[2]

LABEL_KEY = "myometrial_invasion"
DEPTH_KEY = "myometrial_invasion_percent"
NO_ANSWER = "NO_ANSWER"


def outcome(record: dict) -> str:
    """'invasion/depth', or NO_ANSWER."""
    answer = record.get("answer")
    if isinstance(answer, dict) and LABEL_KEY in answer:
        return f"{answer[LABEL_KEY]}/{answer.get(DEPTH_KEY)}"
    return NO_ANSWER


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    """Write one table."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    """Read the groups and write the tables."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--group", action="append", required=True, metavar="NAME=RUN_FOLDER"
    )
    parser.add_argument("--patients-csv", type=Path, required=True, help="column unit")
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    with arguments.patients_csv.open(newline="", encoding="utf-8") as handle:
        patients = [row["unit"] for row in csv.DictReader(handle)]
    by_run, stability, summary, run_folders = [], [], [], {}
    for spec in arguments.group:
        name, _, folder = spec.partition("=")
        runs = sorted(
            Path(folder).glob("rep*"), key=lambda d: int(d.name.removeprefix("rep"))
        )
        run_folders |= {f"{name}/{run.name}": run for run in runs}
        unstable = 0
        for patient in patients:
            seen = []
            for run in runs:
                path = run / "units" / f"{patient}.json"
                if path.is_file():
                    record = json.loads(path.read_text(encoding="utf-8"))
                    seen.append((run.name, outcome(record), record["model_calls"]))
            by_run += [[name, patient, *item] for item in seen]
            if not seen:
                continue
            counts = Counter(item[1] for item in seen)
            calls = [item[2] for item in seen]
            unstable += len(counts) > 1
            stability.append(
                [name, patient, len(seen), len(counts), counts.most_common(1)[0][0],
                 counts.most_common(1)[0][1],
                 "; ".join(f"{k} x{v}" for k, v in counts.most_common()),
                 min(calls), statistics.median(calls), max(calls)]
            )  # fmt: skip
        summary.append([name, len(runs), len(patients), unstable])
    arguments.out.mkdir(parents=True, exist_ok=True)
    write_csv(arguments.out / "patient_by_run.csv",
              ["group", "patient", "run", "outcome", "calls"], by_run)  # fmt: skip
    write_csv(arguments.out / "patient_stability.csv",
              ["group", "patient", "runs", "distinct_outcomes", "modal_outcome",
               "modal_count", "outcomes", "calls_min", "calls_median", "calls_max"],
              stability)  # fmt: skip
    write_csv(arguments.out / "group_summary.csv",
              ["group", "runs", "patients_asked", "patients_with_more_than_one_outcome"],
              summary)  # fmt: skip
    record = build(
        {"patients": Path(os.path.relpath(arguments.patients_csv))},
        run_folders,
        Path(os.path.relpath(REPO_ROOT)),
    )
    # Result folders are outputs, not inputs: leave them out of the uncommitted list.
    record["clinic_repo"]["uncommitted_files"] = [
        f for f in record["clinic_repo"]["uncommitted_files"] if "/results/" not in f
    ]
    (arguments.out / "provenance.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {arguments.out}")


if __name__ == "__main__":
    main()
