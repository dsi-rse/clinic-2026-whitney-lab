"""Compare an OncoTrace run with the human annotations (issue 8).

Writes three text-free CSV files (IDs, offsets, labels, numbers only):

- alignment_annotated.csv: one row per annotated patient (field agreement,
  citation alignment, what was read before answering).
- alignment_spans.csv: one row per annotated span and per run citation.
- reading_coverage_run.csv: one row per run record (all patients).

Then prints a short summary to the terminal.

Example:
    python scripts/evidence_alignment.py
"""

import argparse
import os
from pathlib import Path

import pandas as pd

from oncotrace_bench.alignment import (
    ANSWER_FIELDS,
    annotated_row,
    coverage_row,
    span_rows,
)
from oncotrace_bench.records import (
    ANALYSIS_DIR,
    ANNOTATIONS_DIR,
    DEFAULT_RUN,
    REPORTS_PATH,
    load_annotations,
    load_reports,
    load_run,
)

# Treat a document as "read in full" at or above this fraction.
FULL_READ = 0.99
# Only files the owner can read: outputs sit next to protected data.
PRIVATE_UMASK = 0o077


def parse_args() -> argparse.Namespace:
    """Read command-line options."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--annotations-dir", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument("--reports", type=Path, default=REPORTS_PATH)
    parser.add_argument("--out-dir", type=Path, default=ANALYSIS_DIR)
    return parser.parse_args()


def ids(table: pd.DataFrame) -> str:
    """Return the unit IDs of a table as one comma-separated string."""
    return ", ".join(table["unit"]) if len(table) else "(none)"


def print_agreement(annotated: pd.DataFrame) -> None:
    """Print field-level agreement next to an always-the-majority baseline."""
    answered = annotated[annotated["run_status"] == "answered"]
    print(f"\n## Field agreement ({len(answered)} answered of {len(annotated)})")
    rows = []
    for field in ANSWER_FIELDS:
        majority_value = annotated[f"ann_{field}"].value_counts().idxmax()
        rows.append(
            {
                "field": field,
                "agree": int(answered[f"agree_{field}"].sum()),
                "of": len(answered),
                "majority_value": majority_value,
                "majority_baseline": int(
                    (answered[f"ann_{field}"] == majority_value).sum()
                ),
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))

    present = answered[answered["ann_myometrial_invasion"] == "present"]
    print(
        f"\nPercent field where annotation label is present: "
        f"{int(present['agree_myometrial_invasion_percent'].sum())}/{len(present)}"
    )
    print("\nPercent field, annotation (rows) vs run (columns):")
    print(
        pd.crosstab(
            annotated["ann_myometrial_invasion_percent"],
            annotated["run_myometrial_invasion_percent"].fillna("(no answer)"),
        ).to_string()
    )
    wrong = answered[~answered["agree_myometrial_invasion_percent"].astype(bool)]
    print(f"Percent disagreements: {ids(wrong)}")


def print_citations(annotated: pd.DataFrame) -> None:
    """Print how often the run cites the annotated decisive passages."""
    answered = annotated[annotated["run_status"] == "answered"]
    cites_all = answered[answered["frac_ann_decisive_cited"] == 1.0]
    cites_some = answered[answered["n_ann_decisive_cited"] > 0]
    disjoint = answered[answered["no_shared_passage"].astype(bool)]
    elsewhere = answered[answered["n_run_depth_elsewhere"] > 0]
    in_counter = answered[answered["n_ann_decisive_in_run_counterevidence"] > 0]
    n = len(answered)
    print("\n## Citation alignment (run depth_evidence/quantified_depth)")
    print(f"Cites every annotated decisive span: {len(cites_all)}/{n}")
    print(f"Cites at least one annotated decisive span: {len(cites_some)}/{n}")
    print(f"Cites none of them (entirely different passages): {ids(disjoint)}")
    print(
        f"Has depth_evidence touching no annotated span of any field: "
        f"{len(elsewhere)}/{n} patients, "
        f"{int(answered['n_run_depth_elsewhere'].sum())} of "
        f"{int(answered['n_run_depth_evidence'].sum())} spans"
    )
    print(f"Annotated decisive span cited as counterevidence: {ids(in_counter)}")
    print(
        f"Distinct depth_evidence spans per patient: median "
        f"{answered['n_run_depth_evidence'].median():.0f}, "
        f"range {answered['n_run_depth_evidence'].min()}-"
        f"{answered['n_run_depth_evidence'].max()}"
    )
    print(
        f"Cited any counterevidence: {int(answered['cited_counterevidence'].sum())}/{n}"
    )


def print_reading(annotated: pd.DataFrame, coverage: pd.DataFrame) -> None:
    """Print whether the model read the decisive passage and the whole document."""
    answered = annotated[annotated["run_status"] == "answered"]
    partly = answered[answered["min_frac_decisive_read"] < 1.0]
    never = answered[answered["n_decisive_unread"] > 0]
    print("\n## Read before answering (annotated patients)")
    print(f"Answered without fully reading every decisive span: {ids(partly)}")
    print(f"Answered with some decisive span entirely unread: {ids(never)}")

    print("\n## Whole-document reading (all run records)")
    for column in ["frac_read_before_first_submit", "frac_read_total"]:
        values = coverage[column].dropna()
        print(
            f"{column}: n={len(values)}, median {values.median():.2f}, "
            f"min {values.min():.2f}, read in full {int((values >= FULL_READ).sum())}"
        )
    print(
        f"Reads per record: {coverage['n_reads'].value_counts().sort_index().to_dict()}"
    )
    print(f"Records using search: {int((coverage['n_searches'] > 0).sum())}")
    print(f"Status: {coverage['status'].value_counts().to_dict()}")
    print(
        f"No-answer annotated patients: {ids(annotated[annotated['run_status'] != 'answered'])}"
    )


def main() -> None:
    """Build the alignment tables, save them, and print a summary."""
    args = parse_args()
    os.umask(PRIVATE_UMASK)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    run = load_run(args.run_dir)
    annotations = load_annotations(args.annotations_dir)
    reports = load_reports(args.reports)

    coverage = pd.DataFrame(
        [
            coverage_row(unit, record, reports[unit]["document"])
            for unit, record in run.items()
        ]
    )
    annotated = pd.DataFrame(
        [
            annotated_row(unit, run[unit], annotation, reports[unit]["document"])
            for unit, annotation in annotations.items()
        ]
    )
    spans = pd.DataFrame(
        [
            row
            for unit, annotation in annotations.items()
            for row in span_rows(unit, run[unit], annotation)
        ]
    )

    coverage.to_csv(args.out_dir / "reading_coverage_run.csv", index=False)
    annotated.to_csv(args.out_dir / "alignment_annotated.csv", index=False)
    spans.to_csv(args.out_dir / "alignment_spans.csv", index=False)
    print(f"Wrote 3 CSV files to {args.out_dir}")

    print_agreement(annotated)
    print_citations(annotated)
    print_reading(annotated, coverage)


if __name__ == "__main__":
    main()
