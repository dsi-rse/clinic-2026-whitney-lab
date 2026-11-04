"""Write a roster of the patients that one or more runs left without an answer.

Used for the rescue experiment: rerun only the patients that failed before, with a changed
OncoTrace or setting, and see how many now succeed. Writes `roster_failed_in_issue9.csv`
next to this script by default. No report text is read or written, only patient IDs.

Example:
    python experiments/endometrial_agentic_diagnosis/make_rescue_roster.py \
        --run /path/to/agentic_run --run /path/to/one_shot_run
"""

import argparse
import csv
import json
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
LABEL_KEY = "myometrial_invasion"


def failed_patients(run_dir: Path) -> set[str]:
    """Patients in one run without an accepted answer."""
    failed = set()
    for path in sorted((run_dir / "units").glob("*.json")):
        answer = json.loads(path.read_text(encoding="utf-8")).get("answer")
        if not (isinstance(answer, dict) and LABEL_KEY in answer):
            failed.add(path.stem)
    return failed


def main() -> None:
    """Write the roster."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument(
        "--output", type=Path, default=EXPERIMENT_DIR / "roster_failed_in_issue9.csv"
    )
    arguments = parser.parse_args()
    per_run = [failed_patients(run) for run in arguments.run]
    patients = sorted(set.union(*per_run))
    with arguments.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["unit"])
        writer.writerows([[unit] for unit in patients])
    both = len(set.intersection(*per_run))
    print(
        f"{len(patients)} patients ({both} failed in every run); wrote {arguments.output}"
    )


if __name__ == "__main__":
    main()
