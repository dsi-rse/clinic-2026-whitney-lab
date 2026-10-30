"""Measure how much repeated OncoTrace runs of one configuration differ.

Issue 17 asks whether OncoTrace gives the same answers when the model, code,
configuration and patients are all the same. This script reads two or more runs
of that one configuration and writes labelled tables: how many patients got the
same outcome in every run, how much calls, tokens and refusals vary, where two
runs first stop being identical, and (optionally) how each run agrees with the
human annotations. No report text is written, only counts, patient IDs and
OncoTrace's own reason codes.

Example:
    python experiments/endometrial_determinism/analyze_repeats.py \
        --reps-dir /path/to/runs/determinism_cpu32 --label default_5x
"""

import argparse
import csv
import json
import shutil
import statistics
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
DEFAULT_ANNOTATIONS = REPO_ROOT / "annotations"
DEFAULT_PROJECT = "endo_myometrial_invasion"
DEFAULT_ONCOTRACE = Path("~/oncotrace").expanduser()

# The two answers the task contract asks for.
LABEL_KEY = "myometrial_invasion"
DEPTH_KEY = "myometrial_invasion_percent"
NO_ANSWER = "NO_ANSWER"
# A reply longer than this is a real reasoning reply, not a short tool call.
SUBSTANTIVE_TOKENS = 1000
MIN_RUNS = 2


def write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    """Write one table."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def markdown_table(header: list[str], rows: list[list[Any]]) -> str:
    """Render one table for report.md."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def git_commit(repo: Path) -> str:
    """The commit a repository is at, or 'unknown'."""
    git = shutil.which("git")
    if git is None or not repo.is_dir():
        return "unknown"
    done = subprocess.run(  # noqa: S603 - fixed read-only git arguments
        [git, "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip() if done.returncode == 0 else "unknown"


def load_run(run_dir: Path) -> dict[str, dict[str, Any]]:
    """Read every finished unit record of one run, by patient."""
    records = {}
    for path in sorted((run_dir / "units").glob("*.json")):
        records[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return records


def outcome(record: dict[str, Any]) -> str:
    """One patient's result in one run: 'invasion/depth', or NO_ANSWER."""
    answer = record.get("answer")
    if isinstance(answer, dict) and LABEL_KEY in answer:
        return f"{answer[LABEL_KEY]}/{answer.get(DEPTH_KEY)}"
    return NO_ANSWER


def replies(record: dict[str, Any]) -> list[dict[str, Any]]:
    """The model's replies, in order."""
    return [e for e in record["events"] if e["kind"] == "model_response"]


def completion_tokens(record: dict[str, Any]) -> int:
    """Completion tokens the server reported, summed over every reply."""
    return sum(e.get("completion_tokens") or 0 for e in replies(record))


def refusal_signatures(record: dict[str, Any]) -> list[str]:
    """Why each rejected submission was rejected, in order."""
    return [
        e["signature"] for e in record["events"] if e["kind"] == "recoverable_error"
    ]


def reply_text(event: dict[str, Any]) -> str:
    """Everything the model said in one reply, for comparing two replies."""
    called = json.dumps(event.get("called_tools"), sort_keys=True)
    return f"{event.get('reasoning_text') or ''}|{event.get('assistant_text') or ''}|{called}"


def first_reply(record: dict[str, Any], substantive: bool) -> str | None:
    """The first reply, or the first long reasoning reply, as comparable text."""
    for event in replies(record):
        if (
            not substantive
            or (event.get("completion_tokens") or 0) > SUBSTANTIVE_TOKENS
        ):
            return reply_text(event)
    return None


def spread(values: list[float]) -> dict[str, float]:
    """Mean, standard deviation, minimum and maximum of one patient's counts."""
    return {
        "mean": statistics.fmean(values),
        "sd": statistics.pstdev(values),
        "min": min(values),
        "max": max(values),
    }


def run_rows(
    names: list[str], runs: list[dict[str, dict]], units: list[str]
) -> list[list]:
    """What each run did on the shared patients."""
    rows = []
    for name, run in zip(names, runs, strict=True):
        outcomes = [outcome(run[u]) for u in units]
        rows.append(
            [
                name,
                len(units),
                sum(o != NO_ANSWER for o in outcomes),
                sum(o == NO_ANSWER for o in outcomes),
                sum(run[u]["model_calls"] for u in units),
                sum(completion_tokens(run[u]) for u in units),
                sum(len(refusal_signatures(run[u])) for u in units),
            ]
        )
    return rows


def patient_rows(
    names: list[str], runs: list[dict[str, dict]], units: list[str]
) -> tuple[list[list], list[list]]:
    """One row per patient: each run's outcome, and whether they all match."""
    rows = []
    unstable = []
    for unit in units:
        outcomes = [outcome(run[unit]) for run in runs]
        calls = [run[unit]["model_calls"] for run in runs]
        tokens = [completion_tokens(run[unit]) for run in runs]
        answered = {o for o in outcomes if o != NO_ANSWER}
        distinct = len(set(outcomes))
        if distinct > 1:
            kind = (
                "label differs" if len(answered) > 1 else "answered in some runs only"
            )
            unstable.append(
                [unit, kind, " | ".join(outcomes), " | ".join(map(str, calls))]
            )
        rows.append(
            [
                unit,
                " | ".join(outcomes),
                distinct,
                len(answered),
                " | ".join(map(str, calls)),
                " | ".join(map(str, tokens)),
            ]
        )
    return rows, unstable


def spread_rows(runs: list[dict[str, dict]], units: list[str]) -> list[list]:
    """How much calls, tokens and refusals vary for the same patient."""
    measures = {
        "model calls": lambda r: r["model_calls"],
        "completion tokens": completion_tokens,
        "rejected submissions": lambda r: len(refusal_signatures(r)),
    }
    rows = []
    for label, measure in measures.items():
        per_patient = [spread([measure(run[u]) for run in runs]) for u in units]
        identical = sum(s["max"] == s["min"] for s in per_patient)
        rows.append(
            [
                label,
                f"{identical} / {len(units)}",
                f"{statistics.fmean(s['sd'] for s in per_patient):.1f}",
                f"{max(s['max'] - s['min'] for s in per_patient):.0f}",
            ]
        )
    return rows


def divergence_rows(runs: list[dict[str, dict]], units: list[str]) -> list[list]:
    """Where the runs first stop being identical."""
    rows = []
    for label, substantive in (
        ("first reply (usually a short tool call)", False),
        (f"first long reasoning reply (over {SUBSTANTIVE_TOKENS} tokens)", True),
    ):
        compared = identical = 0
        for unit in units:
            texts = [first_reply(run[unit], substantive) for run in runs]
            if None in texts:
                continue
            compared += 1
            identical += len(set(texts)) == 1
        rows.append([label, f"{identical} / {compared}"])
    return rows


def pairwise_rows(
    names: list[str], runs: list[dict[str, dict]], units: list[str]
) -> list[list]:
    """How often each pair of runs gave the same outcome."""
    rows = []
    for (name_a, run_a), (name_b, run_b) in combinations(
        zip(names, runs, strict=True), 2
    ):
        same = sum(outcome(run_a[u]) == outcome(run_b[u]) for u in units)
        rows.append([name_a, name_b, f"{same} / {len(units)}"])
    return rows


def refusal_rows(
    names: list[str], runs: list[dict[str, dict]], units: list[str]
) -> tuple[list[list], list[str]]:
    """What each run was refused on, by reason code."""
    counts = [
        Counter(s for u in units for s in refusal_signatures(run[u])) for run in runs
    ]
    reasons = sorted(
        {s for c in counts for s in c}, key=lambda s: -sum(c[s] for c in counts)
    )
    return [[reason] + [c[reason] for c in counts] for reason in reasons], [
        "reason",
        *names,
    ]


def annotation_rows(
    names: list[str],
    runs: list[dict[str, dict]],
    units: list[str],
    annotations: Path,
    project: str,
    oncotrace: Path,
) -> list[list]:
    """How each run agrees with the human annotations, on annotated patients."""
    sys.path.insert(0, str(oncotrace / "viewer"))
    import scoring  # TraceView's own agreement rule, so numbers match the viewer

    rows = []
    for field, key in (("invasion", LABEL_KEY), ("depth", DEPTH_KEY)):
        reference = {}
        for path in (annotations / project).glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            reference[data["unit"]] = data["fields"][key]["value"]
        scored = [u for u in units if u in reference]
        for name, run in zip(names, runs, strict=True):
            states = Counter()
            for unit in scored:
                answer = run[unit].get("answer")
                predicted = (
                    answer.get(key)
                    if isinstance(answer, dict) and LABEL_KEY in answer
                    else None
                )
                states[scoring.agreement_state(predicted, reference[unit])] += 1
            rows.append(
                [field, name, len(scored)]
                + [
                    states[s]
                    for s in ("correct", "wrong", "over_committed", "abstained")
                ]
            )
    return rows


def main() -> None:
    """Read the runs, write the tables."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--runs", type=Path, nargs="+", help="two or more run folders")
    parser.add_argument(
        "--reps-dir", type=Path, help="a folder holding rep1, rep2, ..."
    )
    parser.add_argument("--label", required=True, help="name for this result folder")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=EXPERIMENT_DIR / "results",
        help="where to write",
    )
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--oncotrace", type=Path, default=DEFAULT_ONCOTRACE)
    parser.add_argument(
        "--no-annotations", action="store_true", help="skip the annotation table"
    )
    arguments = parser.parse_args()

    folders = list(arguments.runs or [])
    if arguments.reps_dir:
        folders += sorted(arguments.reps_dir.glob("rep*"))
    if len(folders) < MIN_RUNS:
        parser.error("need at least two runs: give --runs or --reps-dir")
    out = arguments.results_dir / arguments.label
    if out.exists():
        parser.error(
            f"{out} already exists; pick a new --label so earlier results are kept"
        )

    names = [folder.name for folder in folders]
    runs = [load_run(folder) for folder in folders]
    units = sorted(set.intersection(*(set(run) for run in runs)))
    if not units:
        parser.error("the runs share no patient with a finished record")

    out.mkdir(parents=True)
    write_csv(
        out / "runs.csv",
        [
            "run",
            "patients",
            "answered",
            "no_answer",
            "model_calls",
            "completion_tokens",
            "rejected_submissions",
        ],
        run_rows(names, runs, units),
    )
    rows, unstable = patient_rows(names, runs, units)
    write_csv(
        out / "per_patient.csv",
        [
            "patient",
            "outcome_per_run",
            "distinct_outcomes",
            "runs_answered",
            "calls_per_run",
            "tokens_per_run",
        ],
        rows,
    )
    write_csv(
        out / "unstable_patients.csv",
        ["patient", "kind", "outcome_per_run", "calls_per_run"],
        unstable,
    )
    spread_table = spread_rows(runs, units)
    write_csv(
        out / "spread.csv",
        ["measure", "identical_in_every_run", "mean_sd_per_patient", "largest_range"],
        spread_table,
    )
    divergence = divergence_rows(runs, units)
    write_csv(out / "divergence.csv", ["reply", "identical_in_every_run"], divergence)
    pairwise = pairwise_rows(names, runs, units)
    write_csv(
        out / "pairwise_agreement.csv", ["run_a", "run_b", "same_outcome"], pairwise
    )
    refusals, refusal_header = refusal_rows(names, runs, units)
    write_csv(out / "refusals.csv", refusal_header, refusals)

    sections = [
        f"# Repeat-run stability: {arguments.label}",
        f"{len(runs)} runs, {len(units)} patients that every run finished "
        f"(patients unfinished in some run are left out, not counted against it).",
        "## What each run did",
        markdown_table(
            [
                "run",
                "patients",
                "answered",
                "no answer",
                "calls",
                "completion tokens",
                "rejected submissions",
            ],
            run_rows(names, runs, units),
        ),
        f"## Patients with the same outcome in every run: "
        f"{len(units) - len(unstable)} of {len(units)} "
        f"(unstable: {len(unstable)}, {100 * len(unstable) / len(units):.0f}%)",
        "An outcome is the invasion and depth answer, or no answer. See "
        "`unstable_patients.csv` for who changed and how.",
        "## How much cost varies for the same patient",
        markdown_table(
            [
                "measure",
                "identical in every run",
                "mean SD per patient",
                "largest range",
            ],
            spread_table,
        ),
        "## Where the runs first differ",
        markdown_table(["reply", "identical in every run"], divergence),
        "## Agreement between pairs of runs",
        markdown_table(["run a", "run b", "same outcome"], pairwise),
    ]
    if not arguments.no_annotations and arguments.annotations.exists():
        table = annotation_rows(
            names,
            runs,
            units,
            arguments.annotations,
            arguments.project,
            arguments.oncotrace,
        )
        header = [
            "field",
            "run",
            "annotated patients",
            "correct",
            "wrong",
            "over_committed",
            "abstained",
        ]
        write_csv(out / "annotation_agreement.csv", header, table)
        sections += [
            "## Agreement with the human annotations",
            markdown_table(header, table),
        ]
    (out / "report.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")

    provenance = {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "runs": [str(folder) for folder in folders],
        "patients_compared": len(units),
        "oncotrace_commit": git_commit(arguments.oncotrace),
        "clinic_commit": git_commit(REPO_ROOT),
    }
    (out / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
