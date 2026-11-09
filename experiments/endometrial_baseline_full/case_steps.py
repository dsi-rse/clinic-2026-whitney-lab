"""Step by step, what each run did on chosen patients (no report text).

Each --run is NAME=FOLDER, where FOLDER holds units/<patient>.json. Only these
fields are read into the tables: the tools the model asked for, the reply's token
count and finish reason, and OncoTrace's own reason codes for refusing a
submission. Replies, quotes and rationales are never written.

Writes two tables:
  case_steps.csv    one row per model call
  case_summary.csv  one row per patient and run

Example:
    python experiments/endometrial_baseline_full/case_steps.py \
        --run new_agentic=/path/to/baseline/rep1 \
        --patients TCGA-AX-A1C8 TCGA-FI-A2EX TCGA-DI-A0WH \
        --out experiments/endometrial_baseline_full/results/some_label/no_answer_cases
"""

import argparse
import csv
import json
from collections import Counter
from itertools import groupby
from pathlib import Path

from compare_modes import answer

STEPS = [
    "patient", "run", "call", "tools_requested", "completion_tokens",
    "finish_reason", "rejections_after_call",
]  # fmt: skip
SUMMARY = [
    "patient", "run", "calls", "calls_before_first_submit", "calls_with_submit",
    "cut_off_calls", "rejected_submissions", "longest_same_rejection_streak",
    "streak_reason", "outcome",
]  # fmt: skip


def steps(record: dict) -> list[dict]:
    """One entry per model call, with the rejections OncoTrace gave after it."""
    calls: list[dict] = []
    for event in record["events"]:
        if event["kind"] == "model_response":
            calls.append(
                {
                    "call": event["model_call"],
                    "tools": list(event.get("called_tools") or []),
                    "tokens": event.get("completion_tokens"),
                    "finish": event.get("finish_reason"),
                    "rejections": [],
                }
            )
        elif event["kind"] == "recoverable_error" and calls:
            calls[-1]["rejections"].append(event["signature"])
    return calls


def summarize(record: dict, calls: list[dict]) -> list:
    """The counts for one patient and run."""
    submit_calls = [c["call"] for c in calls if "submit" in c["tools"]]
    rejected = [code for c in calls for code in c["rejections"]]
    longest, reason = 0, ""
    for code, group in groupby(rejected):
        size = len(list(group))
        if size > longest:
            longest, reason = size, code
    outcome = "answered" if answer(record) is not None else "no answer"
    return [
        record["model_calls"],
        (submit_calls[0] - 1) if submit_calls else len(calls),
        len(submit_calls),
        sum(c["finish"] == "length" for c in calls),
        len(rejected),
        longest,
        reason,
        outcome,
    ]


def main() -> None:
    """Read the runs and write the two tables."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", action="append", required=True, metavar="NAME=FOLDER")
    parser.add_argument("--patients", nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    runs = {}
    for item in arguments.run:
        name, _, folder = item.partition("=")
        runs[name] = Path(folder)
    step_rows, summary_rows = [], []
    for patient in arguments.patients:
        for name, folder in runs.items():
            path = folder / "units" / f"{patient}.json"
            if not path.is_file():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            calls = steps(record)
            for call in calls:
                codes = ", ".join(
                    f"{code} x{n}" for code, n in Counter(call["rejections"]).items()
                )
                step_rows.append(
                    [patient, name, call["call"], "+".join(call["tools"]) or "none",
                     call["tokens"], call["finish"], codes]
                )  # fmt: skip
            summary_rows.append([patient, name, *summarize(record, calls)])

    arguments.out.mkdir(parents=True, exist_ok=True)
    for file, header, rows in (
        ("case_steps.csv", STEPS, step_rows),
        ("case_summary.csv", SUMMARY, summary_rows),
    ):
        with (arguments.out / file).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
    print(f"wrote {len(step_rows)} step rows, {len(summary_rows)} summary rows")


if __name__ == "__main__":
    main()
