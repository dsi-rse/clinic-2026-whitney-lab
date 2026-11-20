"""How much of each report did the model actually read, and does that go with failure?

In agentic mode the model searches a report and reads windows of it. This reads the records
of one or more runs and writes, per patient, how many characters of the report were read, how
many reads and searches it took, and how the patient ended. It then summarises coverage for
answered patients and for patients left without an answer. No report text is written, only
counts, patient IDs and OncoTrace's own reason codes.

Example:
    python experiments/endometrial_agentic_diagnosis/retrieval_coverage.py \
        --run agentic=/path/to/agentic_run --run one_shot=/path/to/one_shot_run --label issue9
"""

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
LABEL_KEY = "myometrial_invasion"
WHOLE_REPORT = 0.99  # read at least this share of the report counts as the whole of it
BUCKETS = (
    (0.0, 0.5, "under half"),
    (0.5, WHOLE_REPORT, "half to nearly all"),
    (WHOLE_REPORT, 1.01, "whole report"),
)


def merged_length(windows: list[tuple[int, int]]) -> int:
    """Characters covered by a set of windows, counting overlaps once."""
    covered, end = 0, -1
    for start, stop in sorted(windows):
        start = max(start, end)
        if stop > start:
            covered += stop - start
            end = stop
    return covered


def inspect_record(record: dict[str, Any]) -> dict[str, Any]:
    """What was read, how many calls it took, and how the patient ended."""
    windows: dict[str, list[tuple[int, int]]] = {}
    lengths: dict[str, int] = {}
    reads = searches = read_windows = 0
    for event in record["events"]:
        if event["kind"] == "read":
            reads += 1
            for window in event["result"]["windows"]:
                document = window["document"]
                windows.setdefault(document, []).append(
                    (window["start"], window["end"])
                )
                lengths[document] = window["document_chars"]
                read_windows += 1
        elif event["kind"] == "search":
            searches += len(event["result"].get("searches", []))
    total = record["document_chars"]
    read = sum(merged_length(spans) for spans in windows.values())
    answer = record.get("answer")
    answered = isinstance(answer, dict) and LABEL_KEY in answer
    reason = next(
        (e.get("reason", "") for e in record["events"] if e["kind"] == "no_answer"), ""
    )
    return {
        "report_chars": total,
        "chars_read": read,
        "coverage": round(min(read / total, 1.0), 3) if total else 0.0,
        "read_calls": reads,
        "windows_read": read_windows,
        "searches": searches,
        "model_calls": record["model_calls"],
        "answered": answered,
        "no_answer_reason": "" if answered else reason,
    }


def bucket(coverage: float) -> str:
    """Which coverage band a patient falls in."""
    return next(name for low, high, name in BUCKETS if low <= coverage < high)


def summary_rows(name: str, found: dict[str, dict[str, Any]]) -> list[list[Any]]:
    """Coverage and effort for answered patients and for patients with no answer."""
    rows = []
    for label, keep in (("answered", True), ("no answer", False), ("all", None)):
        group = [i for i in found.values() if keep is None or i["answered"] == keep]
        if not group:
            continue
        coverage = [i["coverage"] for i in group]
        rows.append(
            [
                name,
                label,
                len(group),
                f"{statistics.median(coverage):.2f}",
                f"{sum(c >= WHOLE_REPORT for c in coverage)} / {len(group)}",
                f"{sum(i['searches'] > 0 for i in group)} / {len(group)}",
                f"{statistics.median(i['read_calls'] for i in group):.0f}",
                f"{statistics.median(i['model_calls'] for i in group):.0f}",
            ]
        )
    return rows


def main() -> None:
    """Read the runs, write the tables."""
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

    patient_rows, summary, bands = [], [], []
    for spec in arguments.run:
        name, _, folder = spec.partition("=")
        found = {
            path.stem: inspect_record(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted((Path(folder) / "units").glob("*.json"))
        }
        patient_rows += [
            [name, unit, *info.values()] for unit, info in sorted(found.items())
        ]
        summary += summary_rows(name, found)
        for _, _, band in BUCKETS:
            group = [i for i in found.values() if bucket(i["coverage"]) == band]
            if group:
                done = sum(i["answered"] for i in group)
                bands.append([name, band, len(group), f"{done} / {len(group)}"])

    header = [
        "run",
        "patient",
        "report_chars",
        "chars_read",
        "coverage",
        "read_calls",
        "windows_read",
        "searches",
        "model_calls",
        "answered",
        "no_answer_reason",
    ]
    with (out / "per_patient.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(patient_rows)
    summary_header = [
        "run",
        "group",
        "patients",
        "median_coverage",
        "read_whole_report",
        "used_search",
        "median_read_calls",
        "median_model_calls",
    ]
    with (out / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(summary_header)
        writer.writerows(summary)
    with (out / "answered_by_coverage_band.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["run", "coverage_band", "patients", "answered"])
        writer.writerows(bands)
    print(f"wrote {out}")
    for row in summary + bands:
        print(row)


if __name__ == "__main__":
    main()
