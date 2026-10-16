"""Triage no_answer patients and refusal effects in an OncoTrace run (issue 8).

Writes two text-free CSV files (IDs, counts, labels, numbers only):

- no_answer_triage.csv: one row per no_answer patient, with a triage class
  (a) evidence not found, (b) refused-submission loop, (c) other budget
  exhaustion, (d) truncation, (e) server error, and the evidence for it.
- refusals_run.csv: one row per patient, with counts of each refusal
  signature and whether the label, percent, or depth basis changed between
  the first submit attempt and the accepted answer.

Then prints a short summary to the terminal.

Example:
    python scripts/triage_no_answers.py
"""

import argparse
import os
from pathlib import Path

import pandas as pd

from oncotrace_bench.records import (
    ANALYSIS_DIR,
    ANNOTATIONS_DIR,
    DEFAULT_RUN,
    load_annotations,
    load_run,
)
from oncotrace_bench.triage import STATED_FIELDS, no_answer_row, refusal_row

# Only files the owner can read: outputs sit next to protected data.
PRIVATE_UMASK = 0o077
# Report-length bins (characters) for the no_answer-rate table.
LENGTH_BINS = [0, 5000, 8000, 12000, 100000]


def parse_args() -> argparse.Namespace:
    """Read command-line options."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--annotations-dir", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument("--out-dir", type=Path, default=ANALYSIS_DIR)
    return parser.parse_args()


def print_triage(triage: pd.DataFrame) -> None:
    """Print the no_answer classes and one line per patient."""
    print(f"\n== no_answer triage ({len(triage)} patients) ==")
    print(triage.groupby(["triage_class", "triage_subtype"]).size().to_string())
    columns = [
        "unit",
        "triage_class",
        "triage_subtype",
        "confidence",
        "annotated",
        "why",
    ]
    print(triage[columns].to_string(index=False))


def print_changes(refusals: pd.DataFrame) -> None:
    """Print whether refused-then-accepted patients changed their answer."""
    answered = refusals[refusals["status"] == "answered"]
    refused_first = answered[~answered["first_submit_accepted"]]
    print(
        f"\n== answer changes: {len(refused_first)} answered patients had their "
        "first submit refused =="
    )
    for field in STATED_FIELDS:
        known = refused_first[refused_first[f"{field}_changed"] != ""]
        changed = known[known[f"{field}_changed"].astype(bool)]
        print(
            f"{field}: changed in {len(changed)} of {len(known)} with a stated "
            f"first value ({', '.join(changed['unit']) or 'none'})"
        )
    accepted_first = answered[answered["first_submit_accepted"]]
    for field in STATED_FIELDS:
        known = accepted_first[accepted_first[f"{field}_changed"] != ""]
        mismatched = known[known[f"{field}_changed"].astype(bool)]
        print(
            f"  check, first submit accepted: stated {field} differs from the "
            f"answer in {len(mismatched)} of {len(known)} (extraction error rate)"
        )


def print_quantified(refusals: pd.DataFrame) -> None:
    """Print how quantified_depth_not_classified refusals were resolved."""
    answered = refusals[refusals["status"] == "answered"].copy()
    column = "n_quantified_depth_not_classified"
    answered["hit_qdnc"] = answered.get(column, pd.Series(0, index=answered.index)) > 0
    print("\n== quantified_depth_not_classified (qdnc) ==")
    print(
        f"patients refused at least once: {int((refusals.get(column, 0) > 0).sum())} "
        f"of {len(refusals)}"
    )
    table = answered.groupby("hit_qdnc").agg(
        patients=("unit", "size"),
        final_quantified_empty=(
            "final_quantified_depth_n",
            lambda n: int((n == 0).sum()),
        ),
        final_explicit_basis=(
            "final_depth_basis",
            lambda b: int((b == "explicit_fraction_or_percentage").sum()),
        ),
    )
    print(table.to_string())


def print_annotated_gap(refusals: pd.DataFrame) -> None:
    """Print no_answer rates for annotated vs other patients by site and length."""
    table = refusals.copy()
    table["no_answer"] = table["status"] == "no_answer"
    table["site"] = table["unit"].str.split("-").str[1]
    table["length_bin"] = pd.cut(table["document_chars"], LENGTH_BINS)
    print("\n== annotated vs other patients ==")
    print(
        table.groupby("annotated")
        .agg(
            patients=("unit", "size"),
            no_answer=("no_answer", "sum"),
            median_chars=("document_chars", "median"),
            median_calls=("model_calls", "median"),
        )
        .to_string()
    )
    print("\nno_answer by report length:")
    print(
        table.groupby(["length_bin", "annotated"], observed=True)["no_answer"]
        .agg(["size", "sum"])
        .to_string()
    )
    print("\nno_answer by tissue source site (first ID block):")
    by_site = table.groupby("site")["no_answer"].agg(["size", "sum"])
    print(by_site.sort_values("size", ascending=False).head(10).to_string())


def main() -> None:
    """Build the two triage tables and print a summary."""
    args = parse_args()
    run = load_run(args.run_dir)
    annotations = load_annotations(args.annotations_dir)

    triage = pd.DataFrame(
        [
            no_answer_row(unit, record, annotations.get(unit))
            for unit, record in run.items()
            if record["answer"]["status"] == "no_answer"
        ]
    )
    refusals = pd.DataFrame(
        [
            refusal_row(unit, record, annotations.get(unit))
            for unit, record in run.items()
        ]
    )
    # Signature count columns are missing where a patient never got that refusal.
    count_columns = [c for c in refusals.columns if c.startswith("n_")]
    refusals[count_columns] = refusals[count_columns].fillna(0).astype(int)

    os.umask(PRIVATE_UMASK)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    triage.to_csv(args.out_dir / "no_answer_triage.csv", index=False)
    refusals.to_csv(args.out_dir / "refusals_run.csv", index=False)
    print(f"wrote {len(triage)} rows to {args.out_dir / 'no_answer_triage.csv'}")
    print(f"wrote {len(refusals)} rows to {args.out_dir / 'refusals_run.csv'}")

    print_triage(triage)
    print_changes(refusals)
    print_quantified(refusals)
    print_annotated_gap(refusals)


if __name__ == "__main__":
    main()
