"""Compare OncoTrace runs made at different temperatures on the annotated patients.

For each run: how many patients were answered, agreement with the annotations
(invasion and depth half), model calls, completion tokens, and stated confidence.
Across repeats of one setting: how many patients changed answer. Against the
baseline setting (t0): which patients used more calls and tokens.

Writes a timestamped results folder with every table, a summary of the numbers,
a provenance record, and a README to write the findings in. Only patient IDs,
labels and counts are written, so the folder can be committed.

The defaults are the runs behind the results in this folder's README. To
analyze other runs, pass them explicitly (from the repo root):

    PYTHONPATH=src python experiments/temperature/compare_temperature.py \
        --run t0=<run> --run t1_r1=<run> --run t1_r2=<run> --run t1_r3=<run>

The part of each label before the first "_" names the setting, so t1_r1 and
t1_r2 count as repeats of t1.
"""

import argparse
import contextlib
import io
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from oncotrace_bench.provenance import build
from oncotrace_bench.records import ANNOTATIONS_DIR, load_annotations, load_run

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent

# The runs behind the first results (oncotrace fc3dadc, GLM-5.3-Flash, job
# 2236218). Group-readable by __oncotrace.
RUNS = Path("/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs")
DEFAULT_RUNS = {
    "t0": RUNS / "2026-10-23_temperature_t0",
    "t1_r1": RUNS / "2026-10-23_temperature_t1_r1",
    "t1_r2": RUNS / "2026-10-23_temperature_t1_r2",
    "t1_r3": RUNS / "2026-10-23_temperature_t1_r3",
}
BASELINE = "t0"

FIELDS = ("myometrial_invasion", "myometrial_invasion_percent")
MIN_REPEATS = 2
LONG_RUN_CALLS = 8

README_TEMPLATE = """# Temperature results: {name}

Made {created} by `{command}`.

| | |
|---|---|
| Runs | {runs} |
| OncoTrace commit | {commits} |
| Task contract | {contracts} |
| Clinic commit | `{clinic_commit}`{dirty} |

All numbers are in `summary.txt`; the tables are the CSV files here. What each
file holds is in the experiment README.

## Findings

_Write the takeaways from `summary.txt` here, in your own words, before
committing this folder._
"""


def run_rows(label: str, run_dir: Path, annotations: dict) -> list[dict]:
    """Return one row per annotated patient that has a record in this run."""
    records = load_run(run_dir)
    rows = []
    for unit, annotation in annotations.items():
        if unit not in records:
            continue
        record = records[unit]
        answer = record["answer"]
        answered = answer["status"] == "answered"
        row = {
            "label": label,
            "setting": label.split("_")[0],
            "unit": unit,
            "status": answer["status"],
            "confidence": answer.get("confidence") if answered else None,
            "model_calls": record["model_calls"],
            "completion_tokens": sum(
                e.get("completion_tokens", 0) for e in record["events"]
            ),
        }
        for field in FIELDS:
            annotated = annotation["fields"][field]["value"]
            row[f"ann_{field}"] = annotated
            row[f"run_{field}"] = answer.get(field) if answered else None
            row[f"agree_{field}"] = answer.get(field) == annotated if answered else None
        rows.append(row)
    return rows


def summarize_run(table: pd.DataFrame) -> pd.DataFrame:
    """One line per run: answered, agreement, calls, tokens, confidence."""
    lines = []
    for label, run in table.groupby("label", sort=False):
        answered = run[run["status"] == "answered"]
        confidence = Counter(answered["confidence"])
        lines.append(
            {
                "run": label,
                "records": len(run),
                "answered": len(answered),
                "invasion_agree": int(answered["agree_myometrial_invasion"].sum()),
                "depth_agree": int(answered["agree_myometrial_invasion_percent"].sum()),
                "depth_cbd": int(
                    (
                        answered["run_myometrial_invasion_percent"]
                        == "cannot_be_determined"
                    ).sum()
                ),
                "calls_mean": round(run["model_calls"].mean(), 1),
                "calls_median": run["model_calls"].median(),
                "calls_max": run["model_calls"].max(),
                f"calls_{LONG_RUN_CALLS}plus": int(
                    (run["model_calls"] >= LONG_RUN_CALLS).sum()
                ),
                "tokens_mean": int(run["completion_tokens"].mean()),
                "tokens_per_call": int(
                    run["completion_tokens"].sum() / run["model_calls"].sum()
                ),
                "high": confidence["high"],
                "medium": confidence["medium"],
                "low": confidence["low"],
            }
        )
    return pd.DataFrame(lines)


def summarize_stability(table: pd.DataFrame) -> pd.DataFrame:
    """Per setting with 2+ repeats: patients whose answer differs between repeats.

    An answer change is counted only between repeats that both answered.
    A patient that answered in some repeats and not others is counted
    separately, because no_answer is a failure, not a different answer.
    """
    lines = []
    for setting, runs in table.groupby("setting", sort=False):
        n_runs = runs["label"].nunique()
        if n_runs < MIN_REPEATS:
            continue
        in_all = runs[runs.groupby("unit")["label"].transform("nunique") == n_runs]
        answered = in_all[in_all["status"] == "answered"]
        answer = (
            answered["run_myometrial_invasion"]
            + "|"
            + answered["run_myometrial_invasion_percent"]
        )
        distinct = answer.groupby(answered["unit"]).nunique()
        changed = distinct[distinct > 1].index
        answered_count = (in_all["status"] == "answered").groupby(in_all["unit"]).sum()
        mixed = answered_count[(answered_count > 0) & (answered_count < n_runs)].index
        lines.append(
            {
                "setting": setting,
                "repeats": n_runs,
                "patients_in_all": in_all["unit"].nunique(),
                "answer_changed": len(changed),
                "answered_sometimes": len(mixed),
                "changed_ids": " ".join(sorted(changed)),
            }
        )
    return pd.DataFrame(lines)


def compare_to_baseline(table: pd.DataFrame) -> pd.DataFrame:
    """Per setting: patients using more or fewer calls and tokens than the baseline.

    Each patient's mean over a setting's repeats is compared with the same
    patient in the baseline run.
    """
    base = table[table["setting"] == BASELINE].set_index("unit")
    lines = []
    for setting, runs in table.groupby("setting", sort=False):
        if setting == BASELINE:
            continue
        mean = runs.groupby("unit")[["model_calls", "completion_tokens"]].mean()
        mean = mean.join(base[["model_calls", "completion_tokens"]], rsuffix="_base")
        calls, base_calls = mean["model_calls"], mean["model_calls_base"]
        ratio = mean["completion_tokens"] / mean["completion_tokens_base"]
        lines.append(
            {
                "setting": setting,
                "patients": len(mean),
                "more_calls": int((calls > base_calls).sum()),
                "fewer_calls": int((calls < base_calls).sum()),
                "same_calls": int((calls == base_calls).sum()),
                "more_tokens": int((ratio > 1).sum()),
                "median_token_ratio": round(ratio.median(), 2),
            }
        )
    return pd.DataFrame(lines)


def parse_args() -> argparse.Namespace:
    """Read the command line; default to the runs behind the first results."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--run",
        action="append",
        metavar="LABEL=FOLDER",
        help="a run folder and its label; repeat for each run (default: the "
        "four runs behind the first results)",
    )
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument(
        "--label", default="", help="optional suffix for the results folder name"
    )
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    args = parser.parse_args()
    if args.run:
        args.runs = {
            label: Path(folder)
            for label, folder in (item.split("=", 1) for item in args.run)
        }
    else:
        args.runs = DEFAULT_RUNS
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
            f"{name} `{Path(run['path']).name}` ({run['records']} records, "
            f"temperature {run.get('temperature')})"
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
    name = f"{stamp}_{args.label}" if args.label else stamp
    out = args.results_dir / name

    annotations = load_annotations(args.annotations)
    rows = []
    for label, folder in args.runs.items():
        rows.extend(run_rows(label, folder, annotations))
    table = pd.DataFrame(rows)

    # Record provenance before writing anything, so the new folder itself is
    # not listed as an uncommitted file.
    prov = build(
        inputs={"roster": EXPERIMENT_DIR / "inputs" / "roster.csv"},
        runs=args.runs,
        repo_root=REPO_ROOT,
        command=" ".join(sys.argv),
        annotations={"path": str(args.annotations), "files": len(annotations)},
    )
    out.mkdir(parents=True)

    per_run = summarize_run(table)
    stability = summarize_stability(table)
    vs_baseline = compare_to_baseline(table)
    table.to_csv(out / "patients.csv", index=False)
    per_run.to_csv(out / "per_run.csv", index=False)
    stability.to_csv(out / "stability.csv", index=False)
    vs_baseline.to_csv(out / "vs_baseline.csv", index=False)

    # Everything printed is kept as summary.txt, then shown.
    printed = io.StringIO()
    with (
        contextlib.redirect_stdout(printed),
        pd.option_context("display.width", 200, "display.max_columns", None),
    ):
        print(f"## Per run ({len(annotations)} annotated patients)")
        print(per_run.to_string(index=False))
        print("\n## Answer changes between repeats")
        print(stability.to_string(index=False) if len(stability) else "(no repeats)")
        print(f"\n## Calls and tokens against {BASELINE}, per patient")
        print(vs_baseline.to_string(index=False) if len(vs_baseline) else "(none)")
    (out / "summary.txt").write_text(printed.getvalue(), encoding="utf-8")
    print(printed.getvalue())

    (out / "provenance.json").write_text(
        json.dumps(prov, indent=2) + "\n", encoding="utf-8"
    )
    write_readme(out, prov)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
