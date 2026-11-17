"""Compare the evidence-buckets arm with the baseline contract on the annotated patients.

Each run is named ARM_repN, where ARM is `baseline` (the main contract) or
`evidence` (the contract copy with an evidence category on each answer). For the
two scored answers, invasion (`myometrial_invasion`) and depth
(`myometrial_invasion_percent`), it writes:

- how answers split across the evidence categories, and how often each category
  agrees with the annotations;
- the four-way split (correct / wrong / over_committed / abstained) per run,
  with the model's `uncertain` counted as abstained, plus the
  always-commonest-answer reference row;
- how many patients change answer between runs, within and between arms;
- how the annotations' cannot_be_determined cases split in the evidence arm;
- patients whose annotation is definite but who get cannot_be_determined;
- the depth category against the annotations' depth_basis;
- the review queue: patients with at least one flagged answer.

Only patient IDs, labels and counts are written, so the folder can be committed.
Run from the clinic repo root:

    PYTHONPATH=src python experiments/evidence_buckets/compare_arms.py \
        --run baseline_rep1=<run> --run baseline_rep2=<run> \
        --run evidence_rep1=<run> --run evidence_rep2=<run>
"""

import argparse
import contextlib
import io
import json
import sys
from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path

import pandas as pd

from oncotrace_bench.provenance import build, not_shared_tag
from oncotrace_bench.records import ANNOTATIONS_DIR, load_annotations, load_run

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent

# The two scored answers, and the evidence-category field beside each.
FIELDS = {
    "myometrial_invasion": "myometrial_invasion_evidence",
    "myometrial_invasion_percent": "myometrial_invasion_percent_evidence",
}
SHORT = {"myometrial_invasion": "invasion", "myometrial_invasion_percent": "depth"}

# Categories in reading order. implied_* are grouped as "implied" in some tables.
CATEGORIES = [
    "explicit",
    "implied_high",
    "implied_medium",
    "implied_low",
    "uncertain",
    "not_present",
    "not_applicable",
]
FLAGGED = {"implied_high", "implied_medium", "implied_low", "uncertain"}

# TraceView's scoring (oncotrace viewer/scoring.py): these annotation values mean
# the annotator gave no definite answer.
UNEVALUABLE = {"not_applicable", "cannot_be_determined"}
STATES = ["correct", "wrong", "over_committed", "abstained"]

# Patients #42 traced; reported in every run.
WATCH = ["TCGA-A5-A0GJ", "TCGA-A5-A0GR"]

README_TEMPLATE = """# Evidence-buckets results: {name}

Made {created} by `{command}`.

| | |
|---|---|
| Runs | {runs} |
| OncoTrace commit | {commits} |
| Task contracts | {contracts} |
| Clinic commit | `{clinic_commit}`{dirty} |

The run folders were made on a laptop through OpenRouter and are not yet on the
shared cluster path; `provenance.json` records this as acknowledged. All numbers
are in `summary.txt`; the tables are the CSV files here. What each table holds
is in the experiment README.

## Findings

_Write the takeaways from `summary.txt` here, in your own words, before
committing this folder._
"""


def agreement_state(predicted: str | None, reference: str) -> str:
    """Score one answer against the annotation, as TraceView does.

    The model's `uncertain` is not a CAP answer: it counts as abstained, the
    same as no answer at all, and is flagged for review.
    """
    if predicted is None or predicted == "uncertain":
        return "abstained"
    if predicted == reference:
        return "correct"
    if reference in UNEVALUABLE and predicted not in UNEVALUABLE:
        return "over_committed"
    return "wrong"


def refusals(record: dict) -> int:
    """Count the submissions OncoTrace refused for this patient."""
    return sum(1 for event in record["events"] if event["kind"] == "recoverable_error")


def run_rows(name: str, run_dir: Path, annotations: dict) -> list[dict]:
    """Return one row per annotated patient that has a record in this run."""
    records = load_run(run_dir)
    arm, rep = name.rsplit("_", 1)
    rows = []
    for unit, annotation in annotations.items():
        if unit not in records:
            continue
        record = records[unit]
        answer = record["answer"]
        answered = answer["status"] == "answered"
        quotes = answer.get("quotes", {}) if answered else {}
        row = {
            "run": name,
            "arm": arm,
            "rep": rep,
            "unit": unit,
            "status": answer["status"],
            "confidence": answer.get("confidence") if answered else None,
            "model_calls": record["model_calls"],
            "refusals": refusals(record),
        }
        for field, evidence in FIELDS.items():
            short = SHORT[field]
            value = answer.get(field) if answered else None
            row[f"{short}_ann"] = annotation["fields"][field]["value"]
            row[f"{short}_model"] = value
            row[f"{short}_category"] = answer.get(evidence) if answered else None
            row[f"{short}_quotes"] = len(quotes.get(field, []))
            row[f"{short}_state"] = agreement_state(value, row[f"{short}_ann"])
        row["depth_basis_ann"] = (
            annotation["fields"]["depth_basis"]["value"] or "(blank)"
        )
        rows.append(row)
    return rows


def per_run(table: pd.DataFrame) -> pd.DataFrame:
    """One line per run: answered, refusals, and how often each answer is cbd or uncertain."""
    lines = []
    for name, run in table.groupby("run", sort=False):
        answered = run[run["status"] == "answered"]
        line = {
            "run": name,
            "records": len(run),
            "answered": len(answered),
            "patients_with_refusal": int((run["refusals"] > 0).sum()),
            "refusals": int(run["refusals"].sum()),
            "calls_mean": round(run["model_calls"].mean(), 1),
        }
        for short in SHORT.values():
            model = answered[f"{short}_model"]
            cbd = model == "cannot_be_determined"
            line[f"{short}_cbd"] = int(cbd.sum())
            line[f"{short}_cbd_with_quotes"] = int(
                (cbd & (answered[f"{short}_quotes"] > 0)).sum()
            )
            line[f"{short}_uncertain"] = int((model == "uncertain").sum())
        lines.append(line)
    return pd.DataFrame(lines)


def four_way(table: pd.DataFrame, annotations: dict) -> pd.DataFrame:
    """Per run and answer: correct, wrong, over_committed and abstained patients.

    The reference row always gives the annotations' commonest value.
    """
    lines = []
    for field, short in SHORT.items():
        values = [a["fields"][field]["value"] for a in annotations.values()]
        commonest, _ = Counter(values).most_common(1)[0]
        states = Counter(agreement_state(commonest, value) for value in values)
        lines.append(
            {
                "answer": short,
                "run": f"always {commonest}",
                "patients": len(values),
                **{state: states[state] for state in STATES},
            }
        )
        for name, run in table.groupby("run", sort=False):
            states = Counter(run[f"{short}_state"])
            lines.append(
                {
                    "answer": short,
                    "run": name,
                    "patients": len(run),
                    **{state: states[state] for state in STATES},
                }
            )
    return pd.DataFrame(lines)


def by_category(table: pd.DataFrame) -> pd.DataFrame:
    """Evidence arm: per run, answer and category, how the answers score."""
    evidence = table[(table["arm"] == "evidence") & (table["status"] == "answered")]
    lines = []
    for name, run in evidence.groupby("run", sort=False):
        for short, category in (
            (short, category) for short in SHORT.values() for category in CATEGORIES
        ):
            rows = run[run[f"{short}_category"] == category]
            if not len(rows):
                continue
            states = Counter(rows[f"{short}_state"])
            lines.append(
                {
                    "run": name,
                    "answer": short,
                    "category": category,
                    "flagged": category in FLAGGED,
                    "answers": len(rows),
                    **{state: states[state] for state in STATES},
                }
            )
    return pd.DataFrame(lines)


def flagged_share(categories: pd.DataFrame) -> pd.DataFrame:
    """Per run and answer: flagged share of all answers vs of disagreements.

    A disagreement is a `wrong` or `over_committed` answer, or an `uncertain`
    where the annotation is definite. This is the pass bar's "useful" test.
    """
    lines = []
    for (name, short), group in categories.groupby(["run", "answer"], sort=False):
        flagged = group[group["flagged"]]
        disagree = group["wrong"] + group["over_committed"]
        lines.append(
            {
                "run": name,
                "answer": short,
                "answers": int(group["answers"].sum()),
                "flagged_answers": int(flagged["answers"].sum()),
                "disagreements": int(disagree.sum()),
                "flagged_disagreements": int(disagree[group["flagged"]].sum()),
            }
        )
    return pd.DataFrame(lines)


def answer_changes(table: pd.DataFrame) -> pd.DataFrame:
    """For every pair of runs: patients whose invasion or depth answer differs.

    Only patients answered in both runs count. `changed_beyond_cbd` treats
    cannot_be_determined and uncertain as the same answer, which removes the
    move between them that the evidence contract intends.
    """
    answered = table[table["status"] == "answered"].set_index(["run", "unit"])

    def key(frame: pd.DataFrame, merge: bool) -> pd.Series:
        invasion = frame["invasion_model"]
        depth = frame["depth_model"]
        if merge:
            invasion = invasion.replace("uncertain", "cannot_be_determined")
            depth = depth.replace("uncertain", "cannot_be_determined")
        return invasion + "|" + depth

    lines = []
    for left, right in combinations(table["run"].unique(), 2):
        a = answered.loc[left]
        b = answered.loc[right]
        both = a.index.intersection(b.index)
        a, b = a.loc[both], b.loc[both]
        changed = both[key(a, False) != key(b, False)]
        beyond = both[key(a, True) != key(b, True)]
        lines.append(
            {
                "left": left,
                "right": right,
                "comparison": "within arm"
                if left.rsplit("_", 1)[0] == right.rsplit("_", 1)[0]
                else "between arms",
                "patients_answered_in_both": len(both),
                "changed": len(changed),
                "changed_beyond_cbd": len(beyond),
                "changed_ids": " ".join(sorted(changed)),
            }
        )
    return pd.DataFrame(lines)


def annotated_cbd_split(table: pd.DataFrame) -> pd.DataFrame:
    """Per run and answer: model answers where the annotation is cannot_be_determined."""
    lines = []
    for name, run in table.groupby("run", sort=False):
        for short in SHORT.values():
            rows = run[run[f"{short}_ann"] == "cannot_be_determined"]
            counts = Counter(rows[f"{short}_model"].fillna("(no answer)"))
            for value, count in sorted(counts.items()):
                lines.append(
                    {"run": name, "answer": short, "model": value, "patients": count}
                )
    return pd.DataFrame(lines)


def new_cbd(table: pd.DataFrame) -> pd.DataFrame:
    """Patients with a definite annotation whose answer is cannot_be_determined."""
    lines = []
    for short in SHORT.values():
        rows = table[
            (table[f"{short}_model"] == "cannot_be_determined")
            & ~table[f"{short}_ann"].isin(UNEVALUABLE)
        ]
        for _, row in rows.iterrows():
            lines.append(
                {
                    "run": row["run"],
                    "answer": short,
                    "unit": row["unit"],
                    "annotation": row[f"{short}_ann"],
                    "quotes": row[f"{short}_quotes"],
                }
            )
    return pd.DataFrame(
        lines, columns=["run", "answer", "unit", "annotation", "quotes"]
    )


def depth_basis_crosstab(table: pd.DataFrame) -> pd.DataFrame:
    """Evidence arm: the annotations' depth_basis against the model's depth category."""
    evidence = table[(table["arm"] == "evidence") & (table["status"] == "answered")]
    cross = pd.crosstab(
        [evidence["run"], evidence["depth_basis_ann"]], evidence["depth_category"]
    )
    present = [c for c in CATEGORIES if c in cross.columns]
    return cross[present].reset_index()


def review_queue(table: pd.DataFrame) -> pd.DataFrame:
    """Evidence arm: patients with at least one flagged answer, and their agreement."""
    evidence = table[(table["arm"] == "evidence") & (table["status"] == "answered")]
    lines = []
    for name, run in evidence.groupby("run", sort=False):
        flagged = run["invasion_category"].isin(FLAGGED) | run["depth_category"].isin(
            FLAGGED
        )
        disagrees = ~(run["invasion_state"] == "correct") | ~(
            run["depth_state"] == "correct"
        )
        lines.append(
            {
                "run": name,
                "answered": len(run),
                "flagged_patients": int(flagged.sum()),
                "flagged_with_a_disagreement": int((flagged & disagrees).sum()),
                "unflagged_with_a_disagreement": int((~flagged & disagrees).sum()),
            }
        )
    return pd.DataFrame(lines)


def watched(table: pd.DataFrame) -> pd.DataFrame:
    """The #42 patients' answers and categories in every run."""
    columns = [
        "run",
        "unit",
        "invasion_ann",
        "invasion_model",
        "invasion_category",
        "depth_ann",
        "depth_model",
        "depth_category",
        "confidence",
    ]
    return table[table["unit"].isin(WATCH)][columns]


def parse_args() -> argparse.Namespace:
    """Read the command line."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        metavar="ARM_repN=FOLDER",
        help="a run folder and its name, e.g. evidence_rep1=<folder>; repeat",
    )
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument(
        "--shared-path",
        default="/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs",
        help="where the laptop run folders will be copied once the cluster is back",
    )
    parser.add_argument("--label", default="", help="suffix for the results folder")
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    args = parser.parse_args()
    args.runs = {
        name: Path(folder) for name, folder in (item.split("=", 1) for item in args.run)
    }
    return args


def write_readme(out: Path, prov: dict) -> None:
    """Write the results folder's README, with the findings left to fill in."""
    runs = prov["runs"]
    commits = sorted({c for run in runs.values() for c in run["oncotrace_commits"]})
    contracts = sorted({c for run in runs.values() for c in run["contract_digests"]})
    clinic = prov["clinic_repo"]
    text = README_TEMPLATE.format(
        name=out.name,
        created=prov["created_utc"],
        command=prov["command"],
        runs=", ".join(
            f"{name} `{Path(run['path']).name}` ({run['records']} records)"
            for name, run in runs.items()
        ),
        commits=", ".join(f"`{commit[:7]}`" for commit in commits),
        contracts=", ".join(f"`{digest[:8]}`" for digest in contracts),
        clinic_commit=clinic["commit"][:7],
        dirty=" (with uncommitted changes)" if clinic["uncommitted_files"] else "",
    )
    (out / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    """Build every table and write one results folder."""
    args = parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = args.results_dir / (f"{stamp}_{args.label}" if args.label else stamp)

    annotations = load_annotations(args.annotations)
    rows = []
    for name, folder in args.runs.items():
        rows.extend(run_rows(name, folder, annotations))
    table = pd.DataFrame(rows)

    # Provenance first, so the new folder is not listed as uncommitted.
    prov = build(
        inputs={
            "roster": REPO_ROOT
            / "experiments/endometrial_baseline_full/roster_annotated66.csv",
            "baseline_config": EXPERIMENT_DIR / "configs/baseline.yaml",
            "evidence_config": EXPERIMENT_DIR / "configs/evidence.yaml",
            "baseline_contract": REPO_ROOT / "tasks/endo_myometrial_invasion.yaml",
        },
        task=EXPERIMENT_DIR / "endo_myometrial_invasion_evidence.yaml",
        runs=args.runs,
        repo_root=REPO_ROOT,
        acknowledged={
            not_shared_tag(name): f"OpenRouter run made on a laptop; to be copied to "
            f"{args.shared_path}/{folder.parent.name}/{folder.name} once the "
            "cluster is back"
            for name, folder in args.runs.items()
        },
        command=" ".join(sys.argv),
        annotations={"path": str(args.annotations), "files": len(annotations)},
    )
    out.mkdir(parents=True)

    categories = by_category(table)
    tables = {
        "patients": table,
        "per_run": per_run(table),
        "four_way": four_way(table, annotations),
        "categories": categories,
        "flagged_share": flagged_share(categories),
        "answer_changes": answer_changes(table),
        "annotated_cbd_split": annotated_cbd_split(table),
        "definite_annotation_model_cbd": new_cbd(table),
        "depth_basis_vs_category": depth_basis_crosstab(table),
        "review_queue": review_queue(table),
        "watched_patients": watched(table),
    }
    for name, frame in tables.items():
        frame.to_csv(out / f"{name}.csv", index=False)

    # Everything printed is kept as summary.txt, then shown.
    printed = io.StringIO()
    with (
        contextlib.redirect_stdout(printed),
        pd.option_context("display.width", 200, "display.max_columns", None),
    ):
        print(f"{len(annotations)} annotated patients\n")
        for name, frame in tables.items():
            if name == "patients":
                continue
            print(f"## {name}")
            print(frame.to_string(index=False) if len(frame) else "(none)")
            print()
    (out / "summary.txt").write_text(printed.getvalue(), encoding="utf-8")
    print(printed.getvalue())

    (out / "provenance.json").write_text(
        json.dumps(prov, indent=2) + "\n", encoding="utf-8"
    )
    write_readme(out, prov)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
