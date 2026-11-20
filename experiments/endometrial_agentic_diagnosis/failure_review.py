"""List every patient a OncoTrace run left without an answer, and why.

Reads one or more run folders and sorts each patient with no accepted answer into
one cause: the model's reply was cut off at the token cap, or it resent the same
reply after the same rejected submission until the calls ran out. Written so it can
be rerun on a run made with a changed setting or a newer OncoTrace, to see whether
those failures went away. No report text is written, only counts, patient IDs and
OncoTrace's own reason codes.

Example:
    python experiments/endometrial_agentic_diagnosis/failure_review.py \
        --run agentic=/path/to/run --run one_shot=/path/to/other_run --label issue9
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
LABEL_KEY = "myometrial_invasion"
SUBSTANTIVE_TOKENS = 200  # shorter replies are tool calls, not repeated reasoning
MIN_LOOP_REPEATS = 4  # the same reply this many times counts as a loop
CUT_OFF = "truncated_without_tool_call"
CATEGORIES = {
    "A": "reply cut off at the token cap, no submission",
    "B": "stuck resending the same reply after the same rejection",
    "C": "call limit used up without a clear loop",
    "D": "other",
}


def inspect_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Why one patient had no answer, or None if the patient was answered."""
    answer = record.get("answer")
    if isinstance(answer, dict) and LABEL_KEY in answer:
        return None
    events = record["events"]
    reason = next((e.get("reason", "") for e in events if e["kind"] == "no_answer"), "")
    refusals = [e["signature"] for e in events if e["kind"] == "recoverable_error"]
    replies = [e for e in events if e["kind"] == "model_response"]
    digests = [
        hashlib.md5(  # noqa: S324 - only compares replies, not a security use
            f"{e.get('assistant_text') or ''}{json.dumps(e.get('called_tools'))}".encode()
        ).hexdigest()
        for e in replies
        if (e.get("completion_tokens") or 0) > SUBSTANTIVE_TOKENS
    ]
    repeats = max(Counter(digests).values()) if digests else 0
    top, times = Counter(refusals).most_common(1)[0] if refusals else ("", 0)
    if reason == CUT_OFF:
        category = "A"
    elif repeats >= MIN_LOOP_REPEATS and times >= repeats // 2:
        category = "B"
    elif reason.startswith("model_call"):
        category = "C"
    else:
        category = "D"
    return {
        "reason": reason,
        "category": category,
        "calls": record["model_calls"],
        "refusals": len(refusals),
        "top_refusal": top,
        "top_refusal_times": times,
        "cut_off_replies": sum(e.get("finish_reason") == "length" for e in replies),
        "identical_reply_repeats": repeats,
    }


def main() -> None:
    """Read the runs, write the table and a count summary."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", action="append", required=True, metavar="NAME=FOLDER")
    parser.add_argument("--label", required=True, help="name for this result folder")
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    arguments = parser.parse_args()

    out = arguments.results_dir / arguments.label
    if out.exists():
        parser.error(
            f"{out} already exists; pick a new --label so earlier results are kept"
        )
    out.mkdir(parents=True)

    rows, summary = [], []
    for spec in arguments.run:
        name, _, folder = spec.partition("=")
        records = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((Path(folder) / "units").glob("*.json"))
        }
        found = {unit: inspect_record(record) for unit, record in records.items()}
        failed = {unit: info for unit, info in found.items() if info}
        counts = Counter(info["category"] for info in failed.values())
        summary.append(
            [name, len(records), len(failed), *(counts[c] for c in CATEGORIES)]
        )
        rows += [[name, unit, *info.values()] for unit, info in sorted(failed.items())]

    header = [
        "run",
        "patient",
        "reason",
        "category",
        "calls",
        "rejected_submissions",
        "most_common_rejection",
        "times",
        "cut_off_replies",
        "identical_reply_repeats",
    ]
    with (out / "no_answer_patients.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    with (out / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "run",
                "patients",
                "no_answer",
                *(f"{k}: {v}" for k, v in CATEGORIES.items()),
            ]
        )
        writer.writerows(summary)
    print(f"wrote {out}")
    for row in summary:
        print(row)


if __name__ == "__main__":
    main()
