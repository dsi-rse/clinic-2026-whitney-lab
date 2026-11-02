"""Make every table of the full-cohort baseline from finished OncoTrace runs.

It runs the three analysis scripts in this folder, records where everything came
from in provenance.json (oncotrace_bench.provenance.build), and writes a results
README whose tables are copied from the CSV files, so no number is typed by hand.
Each call writes a new folder results/<date>_<time>[_label]/ and never
overwrites an earlier one. Only patient IDs, counts and reason codes are written.

Run from the repository root:
    PYTHONPATH=src python experiments/endometrial_baseline_full/run_analysis.py \
        --agentic RUN/rep1 --one-shot RUN2/rep1 --issue9-agentic RUN3 \
        --issue9-one-shot RUN4 --issue17-runs RUN5 --annotations annotations
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from oncotrace_bench.provenance import build

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROSTER_50 = HERE / "roster_annotated50.csv"
CASES = ["TCGA-AX-A1C8", "TCGA-FI-A2EX", "TCGA-DI-A0WH"]
COST_COLUMNS = [
    "mode", "patients", "answered", "no_answer", "calls_mean", "calls_median",
    "calls_max", "patients_using_all_24_calls", "completion_tokens_total",
    "tokens_median", "cut_off_replies", "patients_with_cut_off",
    "rejected_submissions", "patients_with_rejection",
]  # fmt: skip


def run(script: str, *args: object) -> None:
    """Run one analysis script of this folder; stop if it fails."""
    command = [sys.executable, str(HERE / script), *map(str, args)]
    subprocess.run(command, check=True)  # noqa: S603 - our own scripts, fixed arguments


def table(path: Path, columns: list[str] | None = None) -> str:
    """A CSV file as a markdown table (all columns, or the named ones)."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    columns = columns or list(rows[0]) if rows else []
    if not rows:
        return "(no rows)\n"
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(r[c] for c in columns) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def main() -> None:
    """Run the analyses and write the results folder."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--agentic",
        type=Path,
        required=True,
        help="new baseline run (folder with units/)",
    )
    parser.add_argument(
        "--one-shot", type=Path, required=True, help="one_shot run on the same patients"
    )
    parser.add_argument(
        "--issue9-agentic",
        type=Path,
        required=True,
        help="older agentic full run (Issue 9)",
    )
    parser.add_argument(
        "--issue9-one-shot",
        type=Path,
        required=True,
        help="older one_shot full run (Issue 9)",
    )
    parser.add_argument(
        "--issue17-runs",
        type=Path,
        required=True,
        help="folder holding rep1..repN of the 50-patient repeats (Issue 17)",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="annotations folder (one JSON per patient)",
    )
    parser.add_argument("--results-root", type=Path, default=HERE / "results")
    parser.add_argument(
        "--label", default="", help="short name added to the folder name"
    )
    parser.add_argument(
        "--cases", nargs="+", default=CASES, help="patients to follow across runs"
    )
    arguments = parser.parse_args()  # fmt: skip

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = arguments.results_root / (
        stamp + (f"_{arguments.label}" if arguments.label else "")
    )
    out.mkdir(parents=True)  # never overwrite: a second call in the same second fails
    repeats = sorted(arguments.issue17_runs.glob("rep*"))
    named = {
        "agentic_new": arguments.agentic,
        "one_shot_new": arguments.one_shot,
        "agentic_issue9": arguments.issue9_agentic,
        "one_shot_issue9": arguments.issue9_one_shot,
        **{f"issue17_{r.name}": r for r in repeats},
    }
    flags = [f"--run={name}={path}" for name, path in named.items()]
    new_old = [f for f in flags if "issue17" not in f]

    run("summarize_runs.py", *new_old, "--out", out / "full_cohort")
    run(
        "summarize_runs.py",
        *flags,
        "--patients",
        ROSTER_50,
        "--out",
        out / "same_50_patients",
    )
    run(
        "compare_modes.py", "--agentic", arguments.agentic, "--one-shot", arguments.one_shot,
        "--annotations", arguments.annotations, "--annotated-roster", ROSTER_50,
        "--out", out / "mode_comparison",
    )  # fmt: skip
    run(
        "case_across_runs.py",
        *new_old,
        "--patients",
        *arguments.cases,
        "--out",
        out / "no_answer_cases",
    )

    inputs = {"roster_annotated50": ROSTER_50}
    for name in ("full_agentic.yaml", "full_one_shot.yaml"):
        inputs[name] = HERE / name
    record = build(
        inputs, named, REPO,
        arguments={"label": arguments.label, "cases": arguments.cases, "annotations": str(arguments.annotations)},
    )  # fmt: skip
    (out / "provenance.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )

    (out / "README.md").write_text(readme(out, arguments), encoding="utf-8")
    print(f"wrote {out}")


def readme(out: Path, arguments: argparse.Namespace) -> str:
    """The results README: reading guides written here, numbers copied from the CSVs."""
    full = out / "full_cohort"
    same = out / "same_50_patients"
    mode = out / "mode_comparison"
    return f"""# Full-cohort baseline: tables

Made by `run_analysis.py` (see ../../README.md). Only patient IDs, counts and
reason codes are in this folder. `provenance.json` records the runs and files used.
Its `uncommitted_files` lists only this results folder, which was being written
when the record was made; the code that made it is the commit it names.

Run names: `agentic_new` and `one_shot_new` are the updated OncoTrace on all 546
patients; `agentic_issue9` and `one_shot_issue9` are the older full runs of
Issue 9; `issue17_repN` are the five repeats on the 50 annotated patients.
Cost columns count what the model did, not patients' labels.

## 1. All 546 patients: completion and cost ({full.name}/completion_and_cost.csv)
One row per run. A cell counts patients (answered, no_answer, patients_*), model
calls, or completion tokens. `patients_using_all_24_calls` is patients who hit the
call limit. A cut-off reply is one stopped by the 8,192-token limit. A rejected
submission is one OncoTrace refused with a reason code. Compare `no_answer`
(smaller is better) and `calls_mean`/`tokens_median` (smaller is cheaper).

{table(full / "completion_and_cost.csv", COST_COLUMNS)}
Most common rejection codes:

{table(full / "completion_and_cost.csv", ["mode", "top_rejection_codes"])}
## 2. The same 50 annotated patients ({same.name}/completion_and_cost.csv)
Same columns as table 1, but every run is cut down to the 50 patients that have
manual annotations, so runs made on different cohorts can be compared.

{table(same / "completion_and_cost.csv", COST_COLUMNS)}
## 3. Agentic against one_shot, new version ({mode.name}/)
Outcome is `invasion/depth` or NO_ANSWER. `outcome_crosstab.csv` has one row per
pair of outcomes and counts patients. The table below counts patients out of the
50 annotated ones whose answer equals the annotation; no answer counts as not
agreeing. `agentic_only` and `one_shot_only` are patients where only that mode
agrees; `mcnemar_exact_p` tests whether the two differ. These are single runs of
each mode on short single-document reports and one annotator, so this describes
the runs and does not show that one mode is better.

{table(mode / "agreement_with_annotations.csv")}
Patients whose outcome differs between the two modes:

{table(mode / "patients_that_differ.csv")}
## 4. The patients with no answer ({mode.name}/no_answer_patients.csv, no_answer_cases/)
`no_answer_cases/cases_across_runs.csv` follows the patients {', '.join(arguments.cases)}
across every run: outcome, calls, rejected submissions, most common rejection code,
cut-off replies, and OncoTrace's reason for having no answer.

{table(mode / "no_answer_patients.csv")}
"""


if __name__ == "__main__":
    main()
