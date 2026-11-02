"""Show what every run did on chosen patients (counts and reason codes, no report text).

Each --run is NAME=FOLDER, where FOLDER holds units/<patient>.json. The script
writes one row per patient and run that contains the patient.

Example:
    python experiments/endometrial_baseline_full/case_across_runs.py \
        --run new_agentic=/path/to/baseline/rep1 --run issue9=/path/to/issue9_run \
        --patients TCGA-AX-A1C8 TCGA-FI-A2EX TCGA-DI-A0WH \
        --out experiments/endometrial_baseline_full/results/three_no_answer_cases
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

LABEL_KEY = "myometrial_invasion"
DEPTH_KEY = "myometrial_invasion_percent"
HEADER = [
    "patient", "run", "outcome", "calls", "rejected_submissions",
    "top_rejection", "cut_off_replies", "no_answer_reason",
]  # fmt: skip


def main() -> None:
    """Read the runs and write the table."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", action="append", required=True, metavar="NAME=FOLDER")
    parser.add_argument("--patients", nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    runs = {}
    for item in arguments.run:
        name, _, folder = item.partition("=")
        runs[name] = Path(folder)
    rows = []
    for patient in arguments.patients:
        for name, folder in runs.items():
            path = folder / "units" / f"{patient}.json"
            if not path.is_file():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            events = record["events"]
            answer = record.get("answer")
            answered = isinstance(answer, dict) and LABEL_KEY in answer
            outcome = (
                f"{answer[LABEL_KEY]}/{answer.get(DEPTH_KEY)}"
                if answered
                else "NO_ANSWER"
            )
            codes = Counter(
                e["signature"] for e in events if e["kind"] == "recoverable_error"
            )
            replies = [e for e in events if e["kind"] == "model_response"]
            rows.append(
                [
                    patient, name, outcome, record["model_calls"], sum(codes.values()),
                    codes.most_common(1)[0][0] if codes else "",
                    sum(e.get("finish_reason") == "length" for e in replies),
                    next((e.get("reason", "") for e in events if e["kind"] == "no_answer"), ""),
                ]
            )  # fmt: skip
    arguments.out.mkdir(parents=True, exist_ok=True)
    with (arguments.out / "cases_across_runs.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows")


if __name__ == "__main__":
    main()
