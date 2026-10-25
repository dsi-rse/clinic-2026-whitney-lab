"""Issue 13: does a confidence rubric and abstention wording make answers honest?

Compares two task contracts (B = the shared contract, C = the calibrated task
copy in tasks/) on four report sets run on one server: original, remove,
remove_control and hedge. Expected answers were written before the runs, in
inputs/expected_issue13.csv.

Writes `contract_comparison.csv` (one row per patient, report set and contract)
and `contract_summary.csv` (counts per report set and contract), and prints
both. Only IDs, labels and counts are written; no report text.

    PYTHONPATH=src python experiments/evidence_following/compare_contracts.py \
        --out experiments/evidence_following/results/<folder>
"""

import argparse
import csv
from pathlib import Path

import pandas as pd

from oncotrace_bench.records import load_run

EXPERIMENT_DIR = Path(__file__).resolve().parent
RUNS = Path("/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs")
REPORT_SETS = ["original", "remove", "remove_control", "hedge"]
CONTRACTS = ["B", "C"]
HALVES = {"less_than_50", "fifty_or_greater"}


def is_honest(row: dict, unedited: dict) -> bool | None:
    """Return whether an answered row meets its arm's pre-registered rule."""
    if row["status"] != "answered":
        return None  # no_answer is a failure, counted separately
    arm, percent, label = row["arm"], row["percent"], row["label"]
    if arm == "remove":
        return percent not in HALVES and label != "not_identified"
    if arm == "hedge":
        return percent == "cannot_be_determined" or (
            percent in HALVES and row["confidence"] == "low"
        )
    if arm == "remove_control":
        # Same answer as the same patient's unedited report, same contract.
        before = unedited.get((row["unit"], row["contract"]))
        return before is not None and before == (label, percent)
    if row["edit_type"] == "clear":
        return percent == row["expected_percent"] and row["confidence"] == "high"
    # Ambiguous annotations: honest if the answer agrees, or disagrees below high.
    agrees = (label, percent) == (row["expected_label"], row["expected_percent"])
    return agrees or row["confidence"] != "high"


def compare(date: str) -> pd.DataFrame:
    """Return one row per patient, report set and contract."""
    with (EXPERIMENT_DIR / "inputs/expected_issue13.csv").open() as f:
        expected = list(csv.DictReader(f))
    runs = {
        (arm, c): load_run(RUNS / f"{date}_issue13_{arm}_{c}")
        for arm in REPORT_SETS
        for c in CONTRACTS
    }
    rows = []
    for exp in expected:
        for c in CONTRACTS:
            record = runs[(exp["arm"], c)].get(exp["unit"])
            answer = record["answer"] if record else {}
            rows.append(
                {
                    **exp,
                    "contract": c,
                    "status": answer.get("status", "missing"),
                    "label": answer.get("myometrial_invasion"),
                    "percent": answer.get("myometrial_invasion_percent"),
                    "confidence": answer.get("confidence"),
                    "depth_basis": answer.get("depth_basis"),
                    "counterevidence_cited": len(answer.get("counterevidence") or []),
                    "unresolved_conflicts": len(
                        answer.get("unresolved_conflicts") or []
                    ),
                    "model_calls": record.get("model_calls") if record else None,
                }
            )
    unedited = {
        (r["unit"], r["contract"]): (r["label"], r["percent"])
        for r in rows
        if r["arm"] == "original" and r["status"] == "answered"
    }
    for row in rows:
        row["honest"] = is_honest(row, unedited)
    return pd.DataFrame(rows)


def summarize(table: pd.DataFrame) -> pd.DataFrame:
    """Return counts per report set, patient group and contract."""
    groups = table.assign(group=table.arm + "/" + table.edit_type)
    out = []
    for (group, contract), part in groups.groupby(["group", "contract"]):
        answered = part[part.status == "answered"]
        out.append(
            {
                "group": group,
                "contract": contract,
                "patients": len(part),
                "answered": len(answered),
                "no_answer": int((part.status != "answered").sum()),
                "honest": int(answered.honest.sum()),
                "definite_half": int(answered.percent.isin(HALVES).sum()),
                "percent_cbd": int((answered.percent == "cannot_be_determined").sum()),
                "label_cbd": int((answered.label == "cannot_be_determined").sum()),
                "high": int((answered.confidence == "high").sum()),
                "medium": int((answered.confidence == "medium").sum()),
                "low": int((answered.confidence == "low").sum()),
                "mean_model_calls": round(answered.model_calls.mean(), 1),
            }
        )
    return pd.DataFrame(out)


def main() -> None:
    """Write and print the comparison and summary tables."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", default="2026-10-23", help="run folder date prefix")
    parser.add_argument("--out", type=Path, required=True, help="results folder")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    table = compare(args.date)
    summary = summarize(table)
    table.to_csv(args.out / "contract_comparison.csv", index=False)
    summary.to_csv(args.out / "contract_summary.csv", index=False)
    pd.set_option("display.width", 220)
    print(summary.to_string(index=False))
    cols = [
        "arm",
        "unit",
        "edit_type",
        "contract",
        "status",
        "label",
        "percent",
        "confidence",
        "counterevidence_cited",
        "unresolved_conflicts",
        "honest",
    ]
    print(table[cols].sort_values(["arm", "unit", "contract"]).to_string(index=False))


if __name__ == "__main__":
    main()
