"""Run the evidence-following analysis on the original run and the experiment arms.

Reads the original OncoTrace run, the unedited control reruns and the edit arms,
and writes a timestamped results folder with every table, a summary of the
numbers, a provenance record, and a README to write the findings in. Only
patient IDs, offsets, labels and counts are written, so the folder can be
committed.

The defaults are the runs behind the results in this folder's README. To
analyze new runs (after an OncoTrace fix, say), pass them explicitly:

    PYTHONPATH=src python experiments/evidence_following/run_experiment.py \
        --original <run> --controls <run> <run> <run> \
        --arm flip=<run> --arm reword=<run> --label after-fix
"""

import argparse
import contextlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import compare_arms
import evidence_alignment
import evidence_inventory
import triage_no_answers

from oncotrace_bench.provenance import build
from oncotrace_bench.records import (
    ANNOTATIONS_DIR,
    REPORTS_PATH,
    load_annotations,
    load_reports,
    load_run,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent

# The runs behind the first results (oncotrace e901b3f, GLM-5.3-Flash).
# Group-readable by __oncotrace; see the README if one will not open.
RUNS = Path("/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs")
ORIGINAL_RUN = RUNS / "2026-10-09_endometrial_glm53"
CONTROL_RUNS = [RUNS / f"2026-10-13_issue8_s{i}_control" for i in (1, 2, 3)]
EDIT_ARMS = {
    "flip": RUNS / "2026-10-13_issue8_flip",
    "reword": RUNS / "2026-10-13_issue8_reword",
}

README_TEMPLATE = """# Evidence-following results: {name}

Made {created} by `{command}`.

| | |
|---|---|
| Original run | `{original}` ({original_records} records) |
| Control reruns | {controls} |
| Edit arms | {arms} |
| OncoTrace commit of the runs | {commits} |
| Clinic repo commit | `{clinic_commit}`{dirty} |

All numbers are in `summary.txt`; the tables are the CSV and JSON files here.
What each file holds is in the experiment README.

## Key findings

_Write the takeaways from `summary.txt` here, in your own words, before
committing this folder. Say what changed from the previous results folder._
"""


def parse_arm(text: str) -> tuple[str, Path]:
    """Split a NAME=RUN_DIR argument."""
    name, _, path = text.partition("=")
    if not name or not path:
        raise argparse.ArgumentTypeError(f"expected NAME=RUN_DIR, got {text!r}")
    return name, Path(path)


def parse_args() -> argparse.Namespace:
    """Read command-line options."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--original", type=Path, default=ORIGINAL_RUN)
    parser.add_argument("--controls", type=Path, nargs="+", default=CONTROL_RUNS)
    parser.add_argument(
        "--arm",
        type=parse_arm,
        action="append",
        help="edit arm as NAME=RUN_DIR (repeat; default: the flip and reword runs)",
    )
    parser.add_argument("--reports", type=Path, default=REPORTS_PATH)
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument(
        "--curated",
        type=Path,
        default=EXPERIMENT_DIR / "inputs" / "curated_passages.jsonl",
        help="hand-curated depth passages (offsets only)",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        default=EXPERIMENT_DIR / "inputs",
        help="folder with each arm's text-free edits.json",
    )
    parser.add_argument(
        "--label", default="", help="optional suffix for the results folder name"
    )
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    args = parser.parse_args()
    args.arms = dict(args.arm) if args.arm else EDIT_ARMS
    return args


def write_readme(out: Path, prov: dict, args: argparse.Namespace) -> None:
    """Write the results folder's README, with the findings left to fill in."""
    runs = prov["runs"]
    commits = sorted({c for run in runs.values() for c in run["oncotrace_commits"]})
    clinic = prov["clinic_repo"]
    text = README_TEMPLATE.format(
        name=out.name,
        created=prov["created_utc"],
        command=prov["command"],
        original=args.original,
        original_records=runs["original"]["records"],
        controls=", ".join(f"`{path.name}`" for path in args.controls),
        arms=", ".join(f"{name} `{path.name}`" for name, path in args.arms.items()),
        commits=", ".join(f"`{commit[:7]}`" for commit in commits),
        clinic_commit=clinic["commit"][:7],
        dirty=" (with uncommitted changes)" if clinic["uncommitted_files"] else "",
    )
    (out / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    """Run every analysis and write one results folder."""
    args = parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    name = f"{stamp}_{args.label}" if args.label else stamp
    out = args.results_dir / name

    run = load_run(args.original)
    annotations = load_annotations(args.annotations)
    reports = load_reports(args.reports)

    # Record provenance before writing anything, so the new folder itself is
    # not listed as an uncommitted file.
    inputs = {"reports": args.reports, "curated_passages": args.curated}
    for arm in args.arms:
        inputs[f"{arm}_edits"] = args.inputs / arm / "edits.json"
    runs = {"original": args.original}
    runs.update({f"control_{i}": p for i, p in enumerate(args.controls, start=1)})
    runs.update(args.arms)
    prov = build(
        inputs=inputs,
        runs=runs,
        repo_root=REPO_ROOT,
        command=" ".join(sys.argv),
        annotations={"path": str(args.annotations), "files": len(annotations)},
    )
    out.mkdir(parents=True)

    # Everything the analyses print is kept as summary.txt, then shown.
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        print("# Part 1a: answers and citations against the annotations")
        evidence_alignment.write_tables(run, annotations, reports, out)
        print("\n# Part 1b: no-answer triage and refusals")
        triage_no_answers.write_tables(run, annotations, out)
        print("\n# Part 1c: depth-evidence inventory and edit candidates")
        evidence_inventory.write_inventory(run, annotations, reports, args.curated, out)
        print("\n# Part 2: original run vs reruns vs edit arms")
        compare_arms.write_tables(
            args.original, args.controls, args.arms, args.inputs, out
        )
    (out / "summary.txt").write_text(printed.getvalue(), encoding="utf-8")
    print(printed.getvalue())

    (out / "provenance.json").write_text(
        json.dumps(prov, indent=2) + "\n", encoding="utf-8"
    )
    write_readme(out, prov, args)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
