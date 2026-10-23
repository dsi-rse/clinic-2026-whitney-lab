"""Compare an agentic and a one-shot OncoTrace run on the same patients.

Reads two finished (or in-progress) runs through TraceView, pairs them by
patient, and writes a labelled folder of count tables: how many patients each
mode answered, what each spent, what each was refused on, and how each agrees
with the human annotations. No report text is written, only counts, patient IDs
and OncoTrace's own reason codes.

Example:
    python experiments/endometrial_agentic_vs_one_shot/run_comparison.py \
        --agentic /path/to/agentic_run --one-shot /path/to/one_shot_run \
        --label baseline
"""

import argparse
import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from math import comb
from pathlib import Path
from types import ModuleType
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
DEFAULT_TASK = REPO_ROOT / "tasks" / "endo_myometrial_invasion.yaml"
DEFAULT_ANNOTATIONS = REPO_ROOT / "annotations"
DEFAULT_PROJECT = "endo_myometrial_invasion"

# The two answers the task contract asks for, by the key the annotations use.
FIELDS = {"invasion": "myometrial_invasion", "depth": "myometrial_invasion_percent"}
ARMS = {"agentic": "left", "one_shot": "right"}

# `records.Pair` from TraceView, which is imported from the OncoTrace clone at run time.
TraceViewPair = Any


def exact_mcnemar(only_a: int, only_b: int) -> float:
    """Two-sided exact McNemar p-value from the two discordant counts."""
    n = only_a + only_b
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(only_a, only_b) + 1))
    return min(1.0, 2 * tail / 2**n)


def write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    """Write one table."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def markdown_table(header: list[str], rows: list[list[Any]]) -> str:
    """Render a table as GitHub markdown."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def git_state(repo: Path) -> dict[str, Any]:
    """The commit, branch and uncommitted files of a git checkout."""
    git = shutil.which("git")

    def run(*args: str) -> str:
        if git is None or not repo.is_dir():
            return ""
        done = subprocess.run(  # noqa: S603 - fixed read-only git arguments
            [git, "-C", str(repo), *args], capture_output=True, text=True, check=False
        )
        return done.stdout.rstrip() if done.returncode == 0 else ""

    changed = run("status", "--porcelain").splitlines()
    return {
        "path": str(repo),
        "commit": run("rev-parse", "HEAD"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "uncommitted_files": [line[3:] for line in changed],
    }


def run_provenance(run_dir: Path) -> dict[str, Any]:
    """OncoTrace's own provenance record for a run, or {} if it has none."""
    path = run_dir / "provenance.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def outcome_tables(pair: TraceViewPair) -> tuple[list[list[Any]], list[list[Any]]]:
    """Who answered which patients, and why the rest got no answer."""
    groups = pair.outcomes()
    outcome_rows = [
        [name, len(units)]
        for name, units in {
            "both answered": groups["both"],
            "only agentic answered": groups["only_left"],
            "only one_shot answered": groups["only_right"],
            "neither answered": groups["neither"],
        }.items()
    ]
    reasons = {arm: pair.not_answered(side) for arm, side in ARMS.items()}
    reason_rows = [
        [reason, reasons["agentic"][reason], reasons["one_shot"][reason]]
        for reason in sorted(set(reasons["agentic"]) | set(reasons["one_shot"]))
    ]
    return outcome_rows, reason_rows


def refusal_rows(pair: TraceViewPair) -> list[list[Any]]:
    """What each mode was refused on: refusals, and how many patients."""
    by_arm = {arm: pair.refusals(side) for arm, side in ARMS.items()}
    signatures = sorted(set(by_arm["agentic"]) | set(by_arm["one_shot"]))
    rows = []
    for signature in signatures:
        row: list[Any] = [signature]
        for arm in ARMS:
            row += list(by_arm[arm].get(signature, (0, 0)))
        rows.append(row)
    return sorted(rows, key=lambda row: -(row[1] + row[3]))


def agreement_rows(
    pair: TraceViewPair,
    reference: dict[str, str],
    held_out: frozenset[str],
    field: str,
    scoring: ModuleType,
) -> tuple[list[list[Any]], int]:
    """Agreement with the annotations for one field, on patients both modes ran.

    An unanswered patient counts as wrong in `accuracy`. `accuracy_if_answered`
    is shown beside `coverage` because either alone misleads.
    """
    predicted = {}
    server_errors: set[str] = set()
    for arm, side in ARMS.items():
        views = pair.left if side == "left" else pair.right
        predicted[arm], errors = scoring.predictions(list(views.values()), field)
        server_errors |= errors
    units = sorted((set(pair.units) & set(reference)) - held_out - server_errors)
    states = {
        arm: {
            u: scoring.agreement_state(predicted[arm][u], reference[u]) for u in units
        }
        for arm in ARMS
    }
    rows = []
    for arm in ARMS:
        counts = Counter(states[arm].values())
        answered = len(units) - counts["abstained"]
        rows.append(
            [
                arm,
                len(units),
                counts["correct"],
                counts["wrong"],
                counts["over_committed"],
                counts["abstained"],
                f"{answered / len(units):.3f}" if units else "",
                f"{counts['correct'] / len(units):.3f}" if units else "",
                f"{counts['correct'] / answered:.3f}" if answered else "",
            ]
        )
    commonest = Counter(reference[u] for u in units).most_common(1)
    if commonest:
        value, hits = commonest[0]
        rows.append(
            [
                f"always '{value}'",
                len(units),
                hits,
                len(units) - hits,
                0,
                0,
                "1.000",
                f"{hits / len(units):.3f}",
                f"{hits / len(units):.3f}",
            ]
        )
    only_agentic = sum(
        states["agentic"][u] == "correct" and states["one_shot"][u] != "correct"
        for u in units
    )
    only_one_shot = sum(
        states["one_shot"][u] == "correct" and states["agentic"][u] != "correct"
        for u in units
    )
    rows.append(
        [
            "only agentic correct / only one_shot correct",
            only_agentic,
            only_one_shot,
            "",
            "",
            "",
            "",
            "",
            f"McNemar exact p={exact_mcnemar(only_agentic, only_one_shot):.3f}",
        ]
    )
    return rows, len(units)


def disagreement_rows(pair: TraceViewPair) -> list[list[Any]]:
    """Patients where the two modes differ: answered by one, or different values."""
    rows = []
    groups = pair.outcomes()
    for unit in groups["only_left"]:
        rows.append([unit, "only agentic answered", "", pair.right[unit].reason])
    for unit in groups["only_right"]:
        rows.append([unit, "only one_shot answered", pair.left[unit].reason, ""])
    for name, field in FIELDS.items():
        rows += [[unit, f"different {name}", "", ""] for unit in pair.differing(field)]
    return sorted(rows)


def main() -> None:
    """Read both runs, write the tables, the report and the provenance record."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--agentic", type=Path, required=True, help="agentic run folder"
    )
    parser.add_argument(
        "--one-shot", type=Path, required=True, help="one_shot run folder"
    )
    parser.add_argument("--label", required=True, help="name for this result folder")
    parser.add_argument(
        "--oncotrace",
        type=Path,
        default=Path.home() / "oncotrace",
        help="OncoTrace clone that has TraceView's pair() in viewer/records.py",
    )
    parser.add_argument("--task", type=Path, default=DEFAULT_TASK)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    args = parser.parse_args()

    out = EXPERIMENT_DIR / "results" / args.label
    if out.exists():
        sys.exit(
            f"{out} already exists; choose a new --label so earlier results stay put"
        )

    for folder in (args.oncotrace / "viewer", args.oncotrace):
        sys.path.insert(0, str(folder))
    import annotate
    import records
    import scoring

    if not hasattr(records, "pair"):
        sys.exit(
            f"{args.oncotrace} has no records.pair(); use a clone with the paired-compare change"
        )

    tasks, _, _ = records.load_tasks([args.task])
    agentic = records.load_run(args.agentic, tasks)
    one_shot = records.load_run(args.one_shot, tasks)
    pair = records.pair(agentic, one_shot)
    held_out = annotate.development_units(args.annotations, args.project) or frozenset()

    out.mkdir(parents=True)
    outcome, reasons = outcome_tables(pair)
    write_csv(out / "outcome.csv", ["group", "patients"], outcome)
    write_csv(out / "not_answered.csv", ["reason", "agentic", "one_shot"], reasons)
    totals = {arm: pair.totals(side) for arm, side in ARMS.items()}
    total_header = ["arm", *totals["agentic"]]
    total_rows = [[arm, *totals[arm].values()] for arm in ARMS]
    write_csv(out / "totals.csv", total_header, total_rows)
    refusals = refusal_rows(pair)
    refusal_header = [
        "refusal",
        "agentic_refusals",
        "agentic_patients",
        "one_shot_refusals",
        "one_shot_patients",
    ]
    write_csv(out / "refusals.csv", refusal_header, refusals)
    write_csv(
        out / "disagreements.csv",
        ["patient", "kind", "agentic_reason", "one_shot_reason"],
        disagreement_rows(pair),
    )

    agreement_header = [
        "arm",
        "scored",
        "correct",
        "wrong",
        "over_committed",
        "abstained",
        "coverage",
        "accuracy",
        "accuracy_if_answered",
    ]
    sections = []
    scored = {}
    for name, field in FIELDS.items():
        reference, _, _ = annotate.reference_for(args.annotations, args.project, field)
        rows, scored[name] = agreement_rows(pair, reference, held_out, field, scoring)
        write_csv(out / f"agreement_{name}.csv", agreement_header, rows)
        sections.append(
            f"## Agreement with annotations: {name}\n\n"
            + markdown_table(agreement_header, rows)
        )

    report = "\n\n".join(
        [
            f"# Agentic vs one_shot: {args.label}",
            f"Patients both modes ran: {len(pair.units)}. Only agentic: {len(pair.only_left)}. "
            f"Only one_shot: {len(pair.only_right)}. Every table below is over the "
            "patients both modes ran, so neither mode is flattered by having run more.",
            "## Who answered\n\n" + markdown_table(["group", "patients"], outcome),
            "## Why a patient got no answer\n\n"
            + markdown_table(["reason", "agentic", "one_shot"], reasons),
            "## What each mode spent (token counts are the server's own)\n\n"
            + markdown_table(total_header, total_rows),
            "## What each mode was refused on\n\n"
            + markdown_table(
                [
                    "refusal",
                    "agentic refusals",
                    "agentic patients",
                    "one_shot refusals",
                    "one_shot patients",
                ],
                refusals,
            ),
            *sections,
            "Unanswered patients count as wrong in `accuracy`; `over_committed` means the "
            "model gave a definite answer where the annotation says not applicable or "
            "cannot be determined. The annotations are a development reference, not an "
            "independently adjudicated test set. Patients where the modes differ are "
            "listed in `disagreements.csv`.",
        ]
    )
    (out / "report.md").write_text(report + "\n", encoding="utf-8")

    provenance = {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "inputs": {
            "agentic": str(args.agentic),
            "one_shot": str(args.one_shot),
            "task": str(args.task),
            "annotations": str(args.annotations),
            "project": args.project,
        },
        "task_sha256": hashlib.sha256(args.task.read_bytes()).hexdigest(),
        "counts": {
            "agentic_records": len(agentic),
            "one_shot_records": len(one_shot),
            "matched_patients": len(pair.units),
            "scored": scored,
            "held_out_development_patients": len(held_out),
        },
        "agentic_run_provenance": run_provenance(args.agentic),
        "one_shot_run_provenance": run_provenance(args.one_shot),
        "oncotrace": git_state(args.oncotrace),
        "clinic_repo": git_state(REPO_ROOT),
    }
    (out / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
