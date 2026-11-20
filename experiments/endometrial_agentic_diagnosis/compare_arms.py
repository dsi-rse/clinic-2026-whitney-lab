"""Compare each one-setting-changed arm with the baseline repeats.

The baseline is several repeats of the same configuration, so it shows how much two
identical runs already differ. An arm only counts as different on a measure when its value
falls outside the range the baseline repeats span. Everything is taken over the patients
that every run finished. No report text is written, only counts, patient IDs and OncoTrace's
own reason codes.

Example:
    python experiments/endometrial_agentic_diagnosis/compare_arms.py \
        --baseline-dir /path/to/determinism_cpu32 --arms-dir /path/to/diagnosis_arms \
        --label first_comparison
"""

import argparse
import csv
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from math import comb
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
DEFAULT_ANNOTATIONS = REPO_ROOT / "annotations"
DEFAULT_PROJECT = "endo_myometrial_invasion"
DEFAULT_ONCOTRACE = Path("~/oncotrace").expanduser()

LABEL_KEY = "myometrial_invasion"
DEPTH_KEY = "myometrial_invasion_percent"
NO_ANSWER = "NO_ANSWER"
UNEVALUABLE = frozenset({"not_applicable", "cannot_be_determined"})
STATES = ("correct", "wrong", "over_committed", "abstained")


def agreement_state(predicted: str | None, reference: str) -> str:
    """How one answer stands against the annotation (same rule as TraceView's scoring)."""
    if predicted is None:
        return "abstained"
    if predicted == reference:
        return "correct"
    if reference in UNEVALUABLE and predicted not in UNEVALUABLE:
        return "over_committed"
    return "wrong"


def agrees(record: dict[str, Any], key: str, reference: str) -> bool:
    """Whether the patient's answer equals the annotation (no answer counts as not agreeing)."""
    value = record.get("answer")
    return isinstance(value, dict) and value.get(key) == reference


def mcnemar_exact(arm_only: int, base_only: int) -> float:
    """Two-sided exact McNemar p-value from the patients on which the two runs disagree."""
    total = arm_only + base_only
    if total == 0:
        return 1.0
    tail = sum(comb(total, i) for i in range(min(arm_only, base_only) + 1)) / 2**total
    return min(1.0, 2 * tail)


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
    """Every finished unit record of one run, by patient."""
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((run_dir / "units").glob("*.json"))
    }


def answer(record: dict[str, Any]) -> dict[str, Any] | None:
    """The accepted answer, or None when the patient has no answer."""
    value = record.get("answer")
    return value if isinstance(value, dict) and LABEL_KEY in value else None


def outcome(record: dict[str, Any]) -> str:
    """'invasion/depth', or NO_ANSWER."""
    value = answer(record)
    return NO_ANSWER if value is None else f"{value[LABEL_KEY]}/{value.get(DEPTH_KEY)}"


def replies(record: dict[str, Any]) -> list[dict[str, Any]]:
    """The model's replies, in order."""
    return [e for e in record["events"] if e["kind"] == "model_response"]


def tokens(record: dict[str, Any]) -> int:
    """Completion tokens the server reported, over every reply."""
    return sum(e.get("completion_tokens") or 0 for e in replies(record))


def rejections(record: dict[str, Any]) -> int:
    """How many submissions were rejected."""
    return sum(e["kind"] == "recoverable_error" for e in record["events"])


def no_answer_reason(record: dict[str, Any]) -> str:
    """OncoTrace's own reason for having no answer."""
    return next(
        (e.get("reason", "") for e in record["events"] if e["kind"] == "no_answer"), ""
    )


def reference_values(annotations: Path, project: str) -> dict[str, dict[str, str]]:
    """The human annotations, by field then patient."""
    values: dict[str, dict[str, str]] = {"invasion": {}, "depth": {}}
    for path in (annotations / project).glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        values["invasion"][data["unit"]] = data["fields"][LABEL_KEY]["value"]
        values["depth"][data["unit"]] = data["fields"][DEPTH_KEY]["value"]
    return values


def measures(
    run: dict[str, dict], units: list[str], reference: dict[str, dict]
) -> dict[str, int]:
    """Every number we compare, for one run over the shared patients."""
    found = {
        "answered": sum(answer(run[u]) is not None for u in units),
        "model_calls": sum(run[u]["model_calls"] for u in units),
        "completion_tokens": sum(tokens(run[u]) for u in units),
        "rejected_submissions": sum(rejections(run[u]) for u in units),
    }
    for field, key in (("invasion", LABEL_KEY), ("depth", DEPTH_KEY)):
        scored = [u for u in units if u in reference[field]]
        states = Counter(
            agreement_state((answer(run[u]) or {}).get(key), reference[field][u])
            for u in scored
        )
        found.update({f"{field}_{state}": states[state] for state in STATES})
    return found


def modal_outcomes(baseline: list[dict[str, dict]], units: list[str]) -> dict[str, str]:
    """Each patient's most common outcome across the baseline repeats."""
    return {
        u: Counter(outcome(run[u]) for run in baseline).most_common(1)[0][0]
        for u in units
    }


def main() -> None:
    """Read the baseline repeats and the arms, write the comparison."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        help="a folder holding the baseline rep1, rep2, ...",
    )
    parser.add_argument("--baseline-run", type=Path, action="append", default=[])
    parser.add_argument(
        "--arms-dir", type=Path, help="a folder holding one subfolder per arm"
    )
    parser.add_argument("--arm", action="append", default=[], metavar="NAME=FOLDER")
    parser.add_argument("--label", required=True, help="name for this result folder")
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--oncotrace", type=Path, default=DEFAULT_ONCOTRACE)
    arguments = parser.parse_args()

    baseline_dirs = list(arguments.baseline_run)
    if arguments.baseline_dir:
        baseline_dirs += sorted(arguments.baseline_dir.glob("rep*"))
    arms = dict(spec.partition("=")[::2] for spec in arguments.arm)
    if arguments.arms_dir:
        arms.update(
            {
                p.name: str(p)
                for p in sorted(arguments.arms_dir.iterdir())
                if (p / "units").is_dir()
            }
        )
    if len(baseline_dirs) < 2 or not arms:  # noqa: PLR2004 - need a spread and something to compare
        parser.error("need at least two baseline runs and one arm")
    out = arguments.results_dir / arguments.label
    if out.exists():
        parser.error(
            f"{out} already exists; pick a new --label so earlier results are kept"
        )

    baseline = [load_run(folder) for folder in baseline_dirs]
    arm_runs = {name: load_run(Path(folder)) for name, folder in arms.items()}
    units = sorted(set.intersection(*(set(r) for r in [*baseline, *arm_runs.values()])))
    if not units:
        parser.error("the runs share no patient with a finished record")
    out.mkdir(parents=True)
    reference = reference_values(arguments.annotations, arguments.project)

    base_measures = [measures(run, units, reference) for run in baseline]
    spread = {
        k: (min(m[k] for m in base_measures), max(m[k] for m in base_measures))
        for k in base_measures[0]
    }
    rows, outside_count = [], {}
    for name, run in arm_runs.items():
        arm = measures(run, units, reference)
        outside_count[name] = 0
        for key, value in arm.items():
            low, high = spread[key]
            outside = value < low or value > high
            outside_count[name] += outside
            rows.append(
                [name, key, value, f"{low} to {high}", "yes" if outside else "no"]
            )
    write_csv(
        out / "arms_vs_baseline.csv",
        ["arm", "measure", "arm_value", "baseline_range", "outside_baseline_range"],
        rows,
    )

    paired = []
    for name, run in arm_runs.items():
        for field, key in (("invasion", LABEL_KEY), ("depth", DEPTH_KEY)):
            scored = [u for u in units if u in reference[field]]
            for folder, base in zip(baseline_dirs, baseline, strict=True):
                arm_only = base_only = 0
                for unit in scored:
                    in_arm = agrees(run[unit], key, reference[field][unit])
                    in_base = agrees(base[unit], key, reference[field][unit])
                    arm_only += in_arm and not in_base
                    base_only += in_base and not in_arm
                paired.append(
                    [
                        name,
                        field,
                        Path(folder).name,
                        arm_only,
                        base_only,
                        f"{mcnemar_exact(arm_only, base_only):.3f}",
                    ]
                )
    write_csv(
        out / "mcnemar_vs_baseline.csv",
        [
            "arm",
            "field",
            "baseline_run",
            "agrees_only_in_arm",
            "agrees_only_in_baseline",
            "exact_p",
        ],
        paired,
    )

    mode = modal_outcomes(baseline, units)
    unstable = {u for u in units if len({outcome(run[u]) for run in baseline}) > 1}
    changed = []
    for name, run in arm_runs.items():
        for unit in units:
            if outcome(run[unit]) != mode[unit]:
                changed.append(
                    [
                        name,
                        unit,
                        mode[unit],
                        outcome(run[unit]),
                        "baseline unstable here"
                        if unit in unstable
                        else "baseline stable here",
                    ]
                )
    write_csv(
        out / "patients_that_changed.csv",
        ["arm", "patient", "baseline_modal_outcome", "arm_outcome", "note"],
        changed,
    )

    reasons = [
        [
            name,
            *sorted(
                Counter(
                    no_answer_reason(run[u]) for u in units if answer(run[u]) is None
                ).items()
            ),
        ]
        for name, run in arm_runs.items()
    ]
    write_csv(
        out / "no_answer_reasons.csv",
        ["arm", "reasons (reason, count)"],
        [[r[0], *map(str, r[1:])] for r in reasons],
    )

    shown = [
        "answered",
        "model_calls",
        "completion_tokens",
        "rejected_submissions",
        "invasion_correct",
        "invasion_over_committed",
        "depth_correct",
        "depth_over_committed",
    ]
    table = [
        [name] + [next(r[2] for r in rows if r[0] == name and r[1] == k) for k in shown]
        for name in arm_runs
    ]
    table.insert(
        0, ["baseline range"] + [f"{spread[k][0]} to {spread[k][1]}" for k in shown]
    )
    sections = [
        f"# Arms against the baseline repeats: {arguments.label}",
        f"{len(baseline)} baseline repeats, {len(arm_runs)} arms, {len(units)} patients every run finished.",
        "An arm differs on a measure only if it falls outside the baseline range. The range is the "
        "run-to-run spread of identical runs, so a value inside it is not evidence of an effect.",
        "## Key measures",
        markdown_table(["run", *shown], table),
        f"## How many of the {len(spread)} measures fall outside the baseline range",
        markdown_table(
            ["arm", "measures outside range"],
            [[n, c] for n, c in outside_count.items()],
        ),
        f"## Patients whose outcome changed against the baseline's most common outcome: {len(changed)} (arm, patient) pairs",
        "See `patients_that_changed.csv`; read the ones where the baseline is stable first.",
    ]
    (out / "report.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    provenance = {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "baseline_runs": [str(f) for f in baseline_dirs],
        "arms": arms,
        "patients_compared": len(units),
        "oncotrace_commit": git_commit(arguments.oncotrace),
        "clinic_commit": git_commit(REPO_ROOT),
    }
    (out / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    sys.stdout.write(f"wrote {out}\n")


if __name__ == "__main__":
    main()
