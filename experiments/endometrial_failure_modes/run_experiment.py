"""Run the endometrial failure-modes experiment on one OncoTrace run.

Reads a finished (or in-progress) run through TraceView and writes a labelled
results folder: outcome, invasion, depth, confidence and refusal tables, a
text-free summary of chosen patients, a report, and a provenance record.
Each run of the experiment gets its own `--label`, so results from different
OncoTrace versions or annotation sets sit side by side.

Example:
    python experiments/endometrial_failure_modes/run_experiment.py \
        --run ~/oncotrace-work/runs/endometrial_glm53_20261012 \
        --label baseline
"""

import argparse
import json
from pathlib import Path

import pandas as pd
from failure_tables import (
    confidence_table,
    outcome_tables,
    refusal_summary,
)
from provenance import build

from oncotrace_bench.traceview_summary import (
    add_traceview_to_path,
    load_views,
    read_roster,
    trajectory_facts,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
DEFAULT_TASK = REPO_ROOT / "tasks" / "endo_myometrial_invasion.yaml"
DEFAULT_ROSTER = Path(
    "/net/spaces/annawoodard/oncotrace/data/endometrial/roster_ucec.csv"
)
DEFAULT_PROJECT = "endo_myometrial_invasion"
# Patients inspected in the baseline: two budget-exhausted, one truncated, and two
# answered (one recovered from refusals, one clean). Pass --units to inspect others.
DEFAULT_UNITS = [
    "TCGA-A5-A0GP",
    "TCGA-AX-A06F",
    "TCGA-A5-A0GE",
    "TCGA-A5-A0GJ",
    "TCGA-4E-A92E",
]
STEP_KEY = "I=inventory R=read S=search $=submit !=refused ?=other x=no answer"


def markdown_table(frame: pd.DataFrame) -> str:
    """Render a table as GitHub markdown."""
    header = "| " + " | ".join(frame.columns) + " |"
    rule = "|" + "---|" * len(frame.columns)
    rows = [
        "| " + " | ".join(str(cell) for cell in row) + " |"
        for row in frame.itertuples(index=False)
    ]
    return "\n".join([header, rule, *rows])


def patients_markdown(views: list, units: list[str]) -> str:
    """Describe chosen patients' trajectories, with no report text."""
    by_unit = {view.unit: view for view in views}
    lines = [f"# Patient trajectories\n\nStep key: {STEP_KEY}\n"]
    for unit in units:
        lines.append(f"## {unit}\n")
        if unit not in by_unit:
            lines.append("No record in this run.\n")
            continue
        lines.extend(
            f"- {name}: {value}"
            for name, value in trajectory_facts(by_unit[unit]).items()
        )
        lines.append("")
    return "\n".join(lines)


def report_markdown(label: str, tables: dict[str, pd.DataFrame], prov: dict) -> str:
    """Put every table and the headline provenance on one page."""
    counts = prov["counts"]
    lines = [
        f"# Endometrial failure modes: {label}",
        "",
        f"Made {prov['created_utc']} from {counts['run_records']} of "
        f"{counts['roster']} roster patients; {counts['annotations_matched']} of "
        f"{counts['annotations_total']} annotations matched a record. "
        f"OncoTrace commit `{prov['oncotrace']['commit'][:10]}`; see `provenance.json`.",
        "",
    ]
    for name, table in tables.items():
        lines += [f"## {name}", "", markdown_table(table), ""]
    return "\n".join(lines)


def main() -> None:
    """Parse arguments, build every table, and write the results folder."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="OncoTrace run folder")
    parser.add_argument(
        "--label", required=True, help="name for this result set, e.g. baseline"
    )
    parser.add_argument(
        "--task", type=Path, default=DEFAULT_TASK, help="task contract YAML"
    )
    parser.add_argument(
        "--roster", type=Path, default=DEFAULT_ROSTER, help="roster CSV"
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=REPO_ROOT / "annotations",
        help="annotations root",
    )
    parser.add_argument(
        "--project", default=DEFAULT_PROJECT, help="annotation project name"
    )
    parser.add_argument(
        "--units", nargs="+", default=DEFAULT_UNITS, help="patients to inspect"
    )
    parser.add_argument(
        "--oncotrace",
        type=Path,
        default=Path.home() / "oncotrace",
        help="OncoTrace clone that holds viewer/ (TraceView)",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=EXPERIMENT_DIR / "results",
        help="where results go",
    )
    args = parser.parse_args()

    out = args.results_dir / args.label
    if out.exists():
        parser.error(
            f"{out} already exists; choose a new --label so earlier results are kept"
        )

    oncotrace = args.oncotrace.expanduser()
    add_traceview_to_path(oncotrace)
    import annotate

    views, task = load_views(args.run.expanduser(), args.task)
    roster = read_roster(args.roster)
    reference = annotate.reference_for(args.annotations, args.project, task.label_field)

    tables = {
        **outcome_tables(views, task, roster),
        "confidence": confidence_table(views, task, reference),
        "refusals": refusal_summary(views),
    }
    prov = build(
        inputs={
            "run": args.run.expanduser(),
            "task": args.task,
            "roster": args.roster,
            "annotations": args.annotations,
            "project": args.project,
        },
        counts={
            "run_records": len(views),
            "roster": len(roster),
            "annotations_total": len(reference[0]),
            "annotations_matched": len(
                {view.unit for view in views} & set(reference[0])
            ),
        },
        repo_root=REPO_ROOT,
        oncotrace=oncotrace,
    )

    out.mkdir(parents=True)
    for name, table in tables.items():
        table.to_csv(out / f"{name}.csv", index=False)
    (out / "patients.md").write_text(
        patients_markdown(views, args.units), encoding="utf-8"
    )
    (out / "report.md").write_text(
        report_markdown(args.label, tables, prov), encoding="utf-8"
    )
    (out / "provenance.json").write_text(
        json.dumps(prov, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {out}")
    print((out / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
