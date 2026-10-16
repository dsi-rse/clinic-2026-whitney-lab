"""Compare answers across experiment arms: original, control repeats, and edits.

Each arm is a run folder of the same patients. For every patient, this lines
up the answer (status, label, percent) in each arm, says whether an edit arm
moved the answer to the expected value, and, for edit arms, whether the run's
depth citations landed on the edited passages (using the arm's `edits.json`).
"""

import json
from pathlib import Path

from oncotrace_bench.records import load_run, overlap

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
