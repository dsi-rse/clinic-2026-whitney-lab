r"""Compare an experiment's arms: original run, control repeats, and edit arms.

Each arm is a run folder of the same patients. For every patient, this lines
up the answer (status, label, percent) in each arm, says whether an edit arm
moved the answer to the expected value, and, for edit arms, whether the run's
depth citations landed on the edited passages (using the arm's `edits.json`).

    python experiments/evidence_following/compare_arms.py \
        --controls runs/2026-10-13_issue8_s1_control runs/2026-10-13_issue8_s2_control \
        --arm flip=runs/2026-10-13_issue8_flip --arm reword=runs/2026-10-13_issue8_reword

Run folders are relative to the workspace. Writes `arm_comparison.csv` (edited
patients) and `control_noise.csv` (every control patient) to the analysis
folder and prints both. Only IDs, labels, and counts are written.
"""

import argparse
import json
from pathlib import Path

import pandas as pd
from records import ANALYSIS_DIR, DEFAULT_RUN, WORKSPACE, load_run, overlap

FIELDS = ["myometrial_invasion", "myometrial_invasion_percent"]
FLIPPED = {"less_than_50": "fifty_or_greater", "fifty_or_greater": "less_than_50"}


def answer_of(record: dict | None) -> tuple:
    """Return (status, label, percent) for a record, or a missing marker."""
    if record is None:
        return ("missing", None, None)
    answer = record["answer"]
    return (answer.get("status"), *(answer.get(field) for field in FIELDS))


def depth_on_edits(record: dict, edits: list[dict]) -> tuple[int, int]:
    """Return (depth citations touching an edited passage, depth citations)."""
    cites = (record["answer"].get("depth_evidence") or []) + (
        record["answer"].get("quantified_depth") or []
    )
    landed = [
        {"document": e["document"], "start": e["new_start"], "end": e["new_end"]}
        for e in edits
    ]
    touching = sum(any(overlap(c, e) > 0 for e in landed) for c in cites)
    return touching, len(cites)


def compare_arms(
    original: Path, controls: list[Path], edit_arms: dict[str, Path], inputs: Path
) -> list[dict]:
    """Return one row per patient in the edit arms, comparing every arm.

    `edit_arms` maps an arm name (`flip`, `reword`, ...) to its run folder;
    `inputs/<arm>/edits.json` gives where that arm's edits landed.
    """
    base = load_run(original)
    repeats = [load_run(path) for path in controls]
    arms = {name: load_run(path) for name, path in edit_arms.items()}
    manifests = {
        name: json.loads((inputs / name / "edits.json").read_text())
        for name in edit_arms
    }
    units = sorted({e["unit"] for edits in manifests.values() for e in edits})
    rows = []
    for unit in units:
        start = answer_of(base.get(unit))
        row = {"unit": unit, "original": "/".join(map(str, start))}
        repeat_answers = [answer_of(run.get(unit)) for run in repeats]
        for i, answer in enumerate(repeat_answers, start=1):
            row[f"control_{i}"] = "/".join(map(str, answer))
        finished = [a for a in [start, *repeat_answers] if a[0] == "answered"]
        row["control_changes"] = (
            sum(a != finished[0] for a in finished[1:]) if finished else None
        )
        for name, run in arms.items():
            record = run.get(unit)
            answer = answer_of(record)
            row[name] = "/".join(map(str, answer))
            expected = start[2]
            if name == "flip":
                expected = FLIPPED.get(start[2])
            row[f"{name}_as_expected"] = (
                answer[0] == "answered" and answer[2] == expected
            )
            if record is not None and answer[0] == "answered":
                mine = [e for e in manifests[name] if e["unit"] == unit]
                touching, total = depth_on_edits(record, mine)
                row[f"{name}_depth_cites_on_edits"] = f"{touching}/{total}"
        rows.append(row)
    return rows


def noise_rows(original: Path, controls: list[Path]) -> list[dict]:
    """Return one row per control patient, with its answer in every run.

    Also counts how many distinct answers it got across the original run and
    the repeats, which is the run-to-run noise an edit has to stand out from.
    """
    repeats = [load_run(path) for path in controls]
    runs = [load_run(original), *repeats]
    units = sorted({unit for run in repeats for unit in run})
    rows = []
    for unit in units:
        answers = [answer_of(run.get(unit)) for run in runs]
        row = {"unit": unit}
        for name, answer in zip(
            ["original"] + [f"control_{i}" for i in range(1, len(runs))], answers
        ):
            row[name] = "/".join(map(str, answer))
        done = {a for a in answers if a[0] == "answered"}
        row["distinct_answers"] = len(done)
        row["n_answered"] = sum(a[0] == "answered" for a in answers)
        rows.append(row)
    return rows


def main() -> None:
    """Build and print the comparison tables."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--original", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--controls", type=Path, nargs="+", required=True)
    parser.add_argument("--arm", action="append", default=[], help="NAME=RUN_DIR")
    parser.add_argument("--inputs", type=Path, default=ANALYSIS_DIR / "inputs")
    parser.add_argument("--out-dir", type=Path, default=ANALYSIS_DIR)
    args = parser.parse_args()

    controls = [WORKSPACE / path for path in args.controls]
    arms = {}
    for item in args.arm:
        name, _, path = item.partition("=")
        arms[name] = WORKSPACE / path

    noise = pd.DataFrame(noise_rows(args.original, controls))
    noise.to_csv(args.out_dir / "control_noise.csv", index=False)
    print(noise.to_string(index=False))
    print(
        f"\npatients with more than one distinct answer: "
        f"{(noise['distinct_answers'] > 1).sum()} of {len(noise)}\n"
    )

    if arms:
        table = pd.DataFrame(compare_arms(args.original, controls, arms, args.inputs))
        table.to_csv(args.out_dir / "arm_comparison.csv", index=False)
        print(table.to_string(index=False))
        for name in arms:
            hits = table[f"{name}_as_expected"].sum()
            print(f"{name}: {hits} of {len(table)} patients answered as expected")


if __name__ == "__main__":
    main()
