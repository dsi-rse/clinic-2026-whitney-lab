"""Issue 13: does a confidence rubric and abstention wording make answers honest?

Compares two task contracts (B = the shared contract, C = the calibrated task
copy in tasks/) on four report sets run on one server: original, remove,
remove_control and hedge. Expected answers were written before the runs, in
inputs/expected_issue13.csv.

The ambiguous-annotation patients are scored twice: against the raw
annotations (`honest`), and against the revised depth values from Helena's
PR #18 (`honest_pr18`), which are in the same file with their source. The
other report sets score the same either way.

Writes a timestamped results folder with the per-patient table, the counts, the
stated-confidence tally, a summary of the numbers, a provenance record, and a
README to write the findings in. Only IDs, labels and counts are written; no
report text.

The defaults are the runs behind the first results. To analyse other runs
(from the repo root):

    PYTHONPATH=src python experiments/evidence_following/compare_contracts.py \
        --runs-dir <folder> --date <YYYY-MM-DD>

Each of the 8 runs is read from `<runs-dir>/<date>_issue13_<report set>_<B|C>`.
"""

import argparse
import contextlib
import csv
import io
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from oncotrace_bench.provenance import build
from oncotrace_bench.records import load_run

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent

# Where the runs live. Group-readable by __oncotrace, outside Git.
RUNS = Path("/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs")
DEFAULT_DATE = "2026-10-23"

# The GLM-5.3-Flash runs on real reports made before issue 13, for the
# stated-confidence tally in `confidence_by_run.csv`. The two 2026-10-09 smoke
# runs are left out: one is on Qwen3, and both run synthetic SMOKE-NNNN units
# rather than pathology reports, so they do not belong in a statistic about
# behaviour on real reports. These runs predate dsi-rse/oncotrace#6, so they
# still have no_answer records; `provenance.json` records each one's commit.
EARLIER_RUN_NAMES = (
    "2026-10-09_endometrial_glm53",
    "2026-10-13_issue8_flip",
    "2026-10-13_issue8_reword",
    "2026-10-13_issue8_s1_control",
    "2026-10-13_issue8_s2_control",
    "2026-10-13_issue8_s3_control",
)

REPORT_SETS = ["original", "remove", "remove_control", "hedge"]
CONTRACTS = ["B", "C"]
HALVES = {"less_than_50", "fifty_or_greater"}

README_TEMPLATE = """# Issue 13 results: {name}

Made {created} by `{command}`.

| | |
|---|---|
| Runs | {runs} |
| OncoTrace commit | {commits} |
| Task contracts | {contracts} |
| Clinic commit | `{clinic_commit}`{dirty} |
| Expected answers | `inputs/expected_issue13.csv`, written before the runs |
| Earlier runs (confidence tally) | {earlier} |

All numbers are in `summary.txt`; the tables are the CSV files here. What each
file holds is in the experiment README.

`contract_comparison.csv` has one row per patient, report set and contract.
`contract_summary.csv` has the counts, with `honest` scored against the raw
annotations and `honest_pr18` against PR #18's revised depth values.
`confidence_by_run.csv` is the stated-confidence mix per run. None holds
report text.

## Findings

_Write the takeaways from `summary.txt` here, in your own words, before
committing this folder._
"""


def is_honest(row: dict, unedited: dict, expected: tuple[str, str]) -> bool | None:
    """Return whether an answered row meets its arm's pre-registered rule.

    `expected` is the (label, percent) to score against, so the ambiguous
    patients can be scored against either set of expectations.
    """
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
        return percent == expected[1] and row["confidence"] == "high"
    # Ambiguous annotations: honest if the answer agrees, or disagrees below high.
    return (label, percent) == expected or row["confidence"] != "high"


def compare(runs: dict[tuple[str, str], Path]) -> pd.DataFrame:
    """Return one row per patient, report set and contract."""
    with (EXPERIMENT_DIR / "inputs/expected_issue13.csv").open() as f:
        expected = list(csv.DictReader(f))
    records = {key: load_run(path) for key, path in runs.items()}
    rows = []
    for exp in expected:
        for c in CONTRACTS:
            record = records[(exp["arm"], c)].get(exp["unit"])
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
        annotation = (row["expected_label"], row["expected_percent"])
        # A blank pr18 value means PR #18 did not revise this patient.
        revised = (
            row["pr18_label"] or row["expected_label"],
            row["pr18_percent"] or row["expected_percent"],
        )
        row["honest"] = is_honest(row, unedited, annotation)
        row["honest_pr18"] = is_honest(row, unedited, revised)
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
                "honest_pr18": int(answered.honest_pr18.sum()),
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


def confidence_by_run(runs: dict[str, Path]) -> pd.DataFrame:
    """Return the stated-confidence mix of each run, one row per run.

    This is what "its confidence label is uninformative" rests on, so it is
    computed here rather than quoted. `high_share` is of answered records;
    no_answer is a failure, not a confidence level.
    """
    out = []
    for label, path in runs.items():
        records = load_run(path)
        levels = Counter(
            record["answer"].get("confidence")
            for record in records.values()
            if record["answer"]["status"] == "answered"
        )
        answered = sum(levels.values())
        out.append(
            {
                "run": label,
                "folder": Path(path).name,
                "records": len(records),
                "answered": answered,
                "high": levels["high"],
                "medium": levels["medium"],
                "low": levels["low"],
                "high_share": round(levels["high"] / answered, 3) if answered else None,
            }
        )
    table = pd.DataFrame(out)
    totals = table[["records", "answered", "high", "medium", "low"]].sum()
    total_row = {"run": "all", "folder": "", **totals.to_dict()}
    total_row["high_share"] = round(totals["high"] / totals["answered"], 3)
    return pd.concat([table, pd.DataFrame([total_row])], ignore_index=True)


def parse_args() -> argparse.Namespace:
    """Read the command line; default to the runs behind the first results."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--runs-dir", type=Path, default=RUNS, help="folder holding the run folders"
    )
    parser.add_argument(
        "--date", default=DEFAULT_DATE, help="run folder date prefix (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--earlier-runs-dir",
        type=Path,
        default=None,
        help="folder holding the earlier runs for the confidence tally "
        "(default: --runs-dir)",
    )
    parser.add_argument(
        "--label", default="", help="optional suffix for the results folder name"
    )
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    args = parser.parse_args()
    args.runs = {
        (arm, c): args.runs_dir / f"{args.date}_issue13_{arm}_{c}"
        for arm in REPORT_SETS
        for c in CONTRACTS
    }
    earlier_dir = args.earlier_runs_dir or args.runs_dir
    args.earlier_runs = {name: earlier_dir / name for name in EARLIER_RUN_NAMES}
    return args


def write_readme(out: Path, prov: dict) -> None:
    """Write the results folder's README, with the findings left to fill in."""
    runs = prov["runs"]
    issue13 = {k: v for k, v in runs.items() if k not in EARLIER_RUN_NAMES}
    commits = sorted({c for run in issue13.values() for c in run["oncotrace_commits"]})
    contracts = sorted({c for run in issue13.values() for c in run["contract_digests"]})
    clinic = prov["clinic_repo"]
    text = README_TEMPLATE.format(
        name=out.name,
        created=prov["created_utc"],
        command=prov["command"],
        runs=", ".join(
            f"{name} `{Path(run['path']).name}` ({run['records']} records)"
            for name, run in issue13.items()
        ),
        commits=", ".join(f"`{commit[:7]}`" for commit in commits),
        contracts=", ".join(f"`{digest[:8]}`" for digest in contracts),
        clinic_commit=clinic["commit"][:7],
        dirty=" (with uncommitted changes)" if clinic["uncommitted_files"] else "",
        earlier=", ".join(f"`{name}`" for name in EARLIER_RUN_NAMES),
    )
    (out / "README.md").write_text(text, encoding="utf-8")


def shared_inputs() -> dict[str, Path]:
    """The edited reports and their specs, which hold text and stay out of Git.

    Only their paths and SHA-256 go in the provenance record, so the three
    edited arms can be checked against the files they were built from. See the
    experiment README for who can read them.
    """
    shared = Path(
        "/net/spaces/annawoodard/oncotrace/workspaces/khyatt/analysis/issue13/inputs"
    )
    files = {}
    for arm in ("remove", "remove_control", "hedge"):
        files[f"spec_{arm}"] = shared / f"edit_spec_{arm}.json"
        files[f"reports_{arm}"] = shared / arm / "ucec_pathology_report.jsonl"
    return {name: path for name, path in files.items() if path.exists()}


def main() -> None:
    """Build every table and write one results folder."""
    args = parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    name = f"{stamp}_{args.label}" if args.label else stamp
    out = args.results_dir / name

    inputs = {"expected": EXPERIMENT_DIR / "inputs/expected_issue13.csv"}
    inputs["contract_c"] = (
        EXPERIMENT_DIR / "tasks/endo_myometrial_invasion_calibrated.yaml"
    )
    for arm in ("remove", "remove_control", "hedge"):
        inputs[f"roster_{arm}"] = EXPERIMENT_DIR / f"inputs/{arm}/roster.csv"
        inputs[f"edits_{arm}"] = EXPERIMENT_DIR / f"inputs/{arm}/edits.json"
    inputs.update(shared_inputs())

    # Record provenance before writing anything, so the new folder itself is
    # not listed as an uncommitted file.
    prov = build(
        inputs=inputs,
        runs={f"{arm}_{c}": path for (arm, c), path in args.runs.items()}
        | args.earlier_runs,
        repo_root=REPO_ROOT,
        command=" ".join(sys.argv),
        earlier_runs=list(EARLIER_RUN_NAMES),
    )

    table = compare(args.runs)
    summary = summarize(table)
    confidence = confidence_by_run(args.earlier_runs)

    out.mkdir(parents=True)
    table.to_csv(out / "contract_comparison.csv", index=False)
    summary.to_csv(out / "contract_summary.csv", index=False)
    confidence.to_csv(out / "confidence_by_run.csv", index=False)

    # Everything printed is kept as summary.txt, then shown.
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
        "honest_pr18",
    ]
    printed = io.StringIO()
    with (
        contextlib.redirect_stdout(printed),
        pd.option_context("display.width", 220, "display.max_columns", None),
    ):
        print("## Counts per report set and contract")
        print(summary.to_string(index=False))
        print("\n## Stated confidence in the earlier GLM-5.3-Flash runs")
        print(confidence.to_string(index=False))
        print("\n## Every patient, report set and contract")
        print(
            table[cols].sort_values(["arm", "unit", "contract"]).to_string(index=False)
        )
    (out / "summary.txt").write_text(printed.getvalue(), encoding="utf-8")
    print(printed.getvalue())

    (out / "provenance.json").write_text(
        json.dumps(prov, indent=2) + "\n", encoding="utf-8"
    )
    write_readme(out, prov)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
