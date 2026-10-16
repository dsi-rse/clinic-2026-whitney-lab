"""Build the evidence inventory for counterfactual-edit design (issue 8).

Reads the hand-curated passage list (offsets, categories, tags; no report
text) and writes two text-free outputs to the issue 8 analysis folder:

- evidence_inventory.json: every invasion/depth passage per candidate patient,
  with which passages the annotation and the run cited, which passages a
  percent flip or a remove-all edit would have to change, and length-matched
  unrelated control passages for the removal control.
- edit_candidates.csv: one row per patient with counts, flags and the two
  ranking scores (lower is a better edit candidate).

Then prints the counts per classification and the ranked shortlists.

Example:
    python scripts/evidence_inventory.py
"""

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from oncotrace_bench.evidence_inventory import (
    flip_score,
    load_curated,
    removal_score,
    summary_row,
    unit_inventory,
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

# Only files the owner can read: outputs sit next to protected data.
PRIVATE_UMASK = 0o077
SHORTLIST_PER_CLASS = 5


def parse_args() -> argparse.Namespace:
    """Read command-line options."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--curated", type=Path, default=ANALYSIS_DIR / "curated_passages.jsonl"
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--annotations-dir", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument("--reports", type=Path, default=REPORTS_PATH)
    parser.add_argument("--out-dir", type=Path, default=ANALYSIS_DIR)
    return parser.parse_args()


def candidate_units(annotations: dict, run: dict) -> list[str]:
    """Return patients the run got right with a definite half.

    The reference must be `present` with less_than_50 or fifty_or_greater, and
    the run must give the same label and the same half.
    """
    units = []
    for unit, annotation in annotations.items():
        label = annotation["fields"]["myometrial_invasion"]["value"]
        percent = annotation["fields"]["myometrial_invasion_percent"]["value"]
        answer = run.get(unit, {}).get("answer", {})
        if (
            label == "present"
            and percent in ("less_than_50", "fifty_or_greater")
            and answer.get("myometrial_invasion") == label
            and answer.get("myometrial_invasion_percent") == percent
        ):
            units.append(unit)
    return units


def print_shortlist(table: pd.DataFrame, score: str, title: str) -> None:
    """Print the best-scoring patients for one kind of edit, per reference half."""
    print(f"\n{title} (lower score is better)")
    for half, group in table.groupby("reference_percent"):
        best = group.sort_values(score).head(SHORTLIST_PER_CLASS)
        print(
            f"  {half}: "
            + ", ".join(f"{u} ({s:.1f})" for u, s in zip(best["unit"], best[score]))
        )


def main() -> None:
    """Build and save the inventory, then print a summary."""
    args = parse_args()
    os.umask(PRIVATE_UMASK)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    reports = load_reports(args.reports)
    annotations = load_annotations(args.annotations_dir)
    run = load_run(args.run_dir)
    curated = {entry["unit"]: entry for entry in load_curated(args.curated)}

    candidates = candidate_units(annotations, run)
    missing = sorted(set(candidates) - set(curated))
    if missing:
        print("Candidates not yet curated:", ", ".join(missing))

    inventories = [
        unit_inventory(
            curated[unit], reports[unit]["text"], annotations[unit], run[unit]["answer"]
        )
        for unit in candidates
        if unit in curated
    ]
    table = pd.DataFrame([summary_row(inventory) for inventory in inventories])
    table["flip_score"] = table.apply(flip_score, axis=1)
    table["removal_score"] = table.apply(removal_score, axis=1)

    (args.out_dir / "evidence_inventory.json").write_text(
        json.dumps(inventories, indent=1)
    )
    table.to_csv(args.out_dir / "edit_candidates.csv", index=False)

    print(f"{len(candidates)} candidates, {len(inventories)} inventoried")
    print(pd.crosstab(table["classification"], table["reference_percent"]))
    print(
        "stage is the only redundant source:",
        int(table["stage_only_redundancy"].sum()),
        "| stage present:",
        int((table["stage_edition"] != "no_stage").sum()),
    )
    print_shortlist(table, "flip_score", "Percent-flip candidates")
    print_shortlist(table, "removal_score", "Remove-all-evidence candidates")
    print(f"\nWrote evidence_inventory.json and edit_candidates.csv to {args.out_dir}")


if __name__ == "__main__":
    main()
