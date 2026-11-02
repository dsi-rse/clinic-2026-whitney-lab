"""Compare an agentic run and a one_shot run of the same patients.

Reads two OncoTrace run folders (each holds units/<patient>.json) and writes
counts, patient IDs and OncoTrace's own reason codes. No report text is written.
Patients with no answer count as not agreeing with an annotation.

Example:
    python experiments/endometrial_baseline_full/compare_modes.py \
        --agentic /path/to/agentic/rep1 --one-shot /path/to/one_shot/rep1 \
        --annotations annotations/endo_myometrial_invasion \
        --annotated-roster experiments/endometrial_baseline_full/roster_annotated50.csv \
        --out experiments/endometrial_baseline_full/results/mode_comparison
"""

import argparse
import csv
import json
import statistics
from collections import Counter
from math import comb
from pathlib import Path
from typing import Any

LABEL_KEY = "myometrial_invasion"
DEPTH_KEY = "myometrial_invasion_percent"
NO_ANSWER = "NO_ANSWER"
MODES = ("agentic", "one_shot")
CALL_LIMIT = 24  # model calls allowed per patient


def load_run(run_dir: Path) -> dict[str, dict[str, Any]]:
    """Every finished unit record of one run, by patient."""
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((run_dir / "units").glob("*.json"))
    }


def answer(record: dict[str, Any]) -> dict[str, Any] | None:
    """The accepted answer, or None when the patient has no answer."""
    value = record.get("answer")
    return value if isinstance(value, dict) and LABEL_KEY in value else None


def outcome(record: dict[str, Any]) -> str:
    """'invasion/depth', or NO_ANSWER."""
    value = answer(record)
    return NO_ANSWER if value is None else f"{value[LABEL_KEY]}/{value.get(DEPTH_KEY)}"


def replies(record: dict[str, Any]) -> list[dict[str, Any]]:
    """The model's replies, in order."""
    return [e for e in record["events"] if e["kind"] == "model_response"]


def tokens(record: dict[str, Any]) -> int:
    """Completion tokens over every reply."""
    return sum(e.get("completion_tokens") or 0 for e in replies(record))


def cut_offs(record: dict[str, Any]) -> int:
    """Replies stopped by the token cap."""
    return sum(e.get("finish_reason") == "length" for e in replies(record))


def refusals(record: dict[str, Any]) -> list[str]:
    """Reason codes of the rejected submissions."""
    return [
        e["signature"] for e in record["events"] if e["kind"] == "recoverable_error"
    ]


def no_answer_reason(record: dict[str, Any]) -> str:
    """OncoTrace's own reason for having no answer."""
    return next(
        (e.get("reason", "") for e in record["events"] if e["kind"] == "no_answer"), ""
    )


def percentile(values: list[int], share: float) -> float:
    """Nearest-rank percentile."""
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Two-sided exact McNemar p-value from the patients on which two runs disagree."""
    total = only_a + only_b
    if total == 0:
        return 1.0
    tail = sum(comb(total, i) for i in range(min(only_a, only_b) + 1)) / 2**total
    return min(1.0, 2 * tail)


def write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    """Write one table."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def references(folder: Path) -> dict[str, dict[str, str]]:
    """The human annotations, by field then patient."""
    values: dict[str, dict[str, str]] = {"invasion": {}, "depth": {}}
    for path in folder.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        values["invasion"][data["unit"]] = data["fields"][LABEL_KEY]["value"]
        values["depth"][data["unit"]] = data["fields"][DEPTH_KEY]["value"]
    return values


def summary_rows(runs: dict[str, dict[str, dict]]) -> list[list[Any]]:
    """Completion and cost, one row per mode."""
    rows = []
    for mode, run in runs.items():
        records = list(run.values())
        calls = [r["model_calls"] for r in records]
        used = [tokens(r) for r in records]
        codes = Counter(code for r in records for code in refusals(r))
        rows.append(
            [
                mode,
                len(records),
                sum(answer(r) is not None for r in records),
                sum(answer(r) is None for r in records),
                round(statistics.mean(calls), 2),
                statistics.median(calls),
                max(calls),
                sum(c == CALL_LIMIT for c in calls),
                sum(used),
                statistics.median(used),
                percentile(used, 0.9),
                max(used),
                sum(cut_offs(r) for r in records),
                sum(cut_offs(r) > 0 for r in records),
                sum(len(refusals(r)) for r in records),
                sum(len(refusals(r)) > 0 for r in records),
                "; ".join(f"{k} {v}" for k, v in codes.most_common(5)),
            ]
        )
    return rows


SUMMARY_HEADER = [
    "mode", "patients", "answered", "no_answer", "calls_mean", "calls_median",
    "calls_max", "patients_using_all_24_calls", "completion_tokens_total",
    "tokens_median", "tokens_p90", "tokens_max", "cut_off_replies",
    "patients_with_cut_off", "rejected_submissions", "patients_with_rejection",
    "top_rejection_codes",
]  # fmt: skip


def main() -> None:
    """Read both runs, write the tables."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--agentic", type=Path, required=True)
    parser.add_argument("--one-shot", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument(
        "--annotated-roster",
        type=Path,
        required=True,
        help="CSV (column unit) of the patients to score; the single-annotator 50",
    )
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    runs = {
        "agentic": load_run(arguments.agentic),
        "one_shot": load_run(arguments.one_shot),
    }
    units = sorted(set(runs["agentic"]) & set(runs["one_shot"]))
    arguments.out.mkdir(parents=True, exist_ok=True)
    write_csv(
        arguments.out / "completion_and_cost.csv", SUMMARY_HEADER, summary_rows(runs)
    )

    outcomes = {m: {u: outcome(runs[m][u]) for u in units} for m in MODES}
    cross = Counter((outcomes["agentic"][u], outcomes["one_shot"][u]) for u in units)
    write_csv(
        arguments.out / "outcome_crosstab.csv",
        ["agentic_outcome", "one_shot_outcome", "patients"],
        [[a, o, n] for (a, o), n in sorted(cross.items())],
    )
    differ = [u for u in units if outcomes["agentic"][u] != outcomes["one_shot"][u]]
    write_csv(
        arguments.out / "patients_that_differ.csv",
        ["patient", "agentic_outcome", "one_shot_outcome", "agentic_calls", "one_shot_calls"],
        [
            [u, outcomes["agentic"][u], outcomes["one_shot"][u],
             runs["agentic"][u]["model_calls"], runs["one_shot"][u]["model_calls"]]
            for u in differ
        ],
    )  # fmt: skip
    write_csv(
        arguments.out / "no_answer_patients.csv",
        ["mode", "patient", "reason", "calls", "rejected_submissions", "cut_off_replies"],
        [
            [m, u, no_answer_reason(runs[m][u]), runs[m][u]["model_calls"],
             len(refusals(runs[m][u])), cut_offs(runs[m][u])]
            for m in MODES for u in units if answer(runs[m][u]) is None
        ],
    )  # fmt: skip

    with arguments.annotated_roster.open(newline="", encoding="utf-8") as handle:
        scored_units = {row["unit"] for row in csv.DictReader(handle)}
    reference = references(arguments.annotations)
    rows = []
    for field, key in (("invasion", LABEL_KEY), ("depth", DEPTH_KEY)):
        scored = [u for u in units if u in reference[field] and u in scored_units]
        agree = {
            m: {
                u: (answer(runs[m][u]) or {}).get(key) == reference[field][u]
                for u in scored
            }
            for m in MODES
        }
        only_agentic = sum(
            agree["agentic"][u] and not agree["one_shot"][u] for u in scored
        )
        only_one_shot = sum(
            agree["one_shot"][u] and not agree["agentic"][u] for u in scored
        )
        rows.append(
            [field, len(scored), sum(agree["agentic"].values()),
             sum(agree["one_shot"].values()), only_agentic, only_one_shot,
             round(mcnemar_exact(only_agentic, only_one_shot), 3)]
        )  # fmt: skip
    write_csv(
        arguments.out / "agreement_with_annotations.csv",
        ["field", "annotated_patients", "agentic_agrees", "one_shot_agrees",
         "agentic_only", "one_shot_only", "mcnemar_exact_p"],
        rows,
    )  # fmt: skip
    print(f"wrote {arguments.out}: {len(units)} shared patients, {len(differ)} differ")


if __name__ == "__main__":
    main()
