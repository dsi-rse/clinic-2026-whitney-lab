r"""Make edited report copies for an evidence-following experiment arm.

Two steps, so a person writes every replacement by hand:

    # 1. Write a spec with the passages to edit and empty replacements
    python experiments/evidence_following/report_edits.py template \
        --arm flip --inventory results/<timestamp>/evidence_inventory.json \
        --units TCGA-A5-A0GI ...

    # 2. Fill in each "replacement" in the spec, then apply it
    python experiments/evidence_following/report_edits.py apply --arm flip

Arms: flip, reword and hedge (same passages as flip), remove, remove_control.

The spec is a JSON list of edits, one per passage:

    {"unit": ..., "start": ..., "end": ..., "kind": "flip",
     "original_sha256": ..., "original": ..., "replacement": ...}

`start` and `end` are offsets into the ORIGINAL report. `original` is there
only so the person writing `replacement` can see what they are replacing;
`original_sha256` is what the script checks, so a spec made from a different
report version is refused.

Applying a spec writes `<inputs>/<arm>/` with a new report store holding only
the edited units, a roster for them, and a text-free manifest (`edits.json`)
of where each edit landed in the edited text. The original store is never
written to. Specs and edited stores hold report text, so they stay in the
shared workspace (`--inputs`), never in Git. The text-free roster and manifest
are also copied into this experiment's `inputs/<arm>/`, which is committed and
read by run_experiment.py. The script prints only counts and problems.
"""

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

from oncotrace_bench.records import REPORTS_PATH, load_reports

EXPERIMENT_DIR = Path(__file__).resolve().parent
# Where the issue 8 specs and edited stores live. Group-readable, outside Git.
SHARED_INPUTS = Path(
    "/net/spaces/annawoodard/oncotrace/workspaces/khyatt/analysis/issue8/inputs"
)


def sha256(text: str) -> str:
    """Return the sha256 hex digest of a string."""
    return hashlib.sha256(text.encode()).hexdigest()


def template_edits(
    reports: dict[str, dict], inventory: list[dict], units: list[str], arm: str
) -> list[dict]:
    """Return an edit spec with an empty `replacement` for each passage to edit.

    The passages come from the evidence inventory: those marked `flip_edit` for
    the `flip`, `reword` and `hedge` arms, `removal_edit` for `remove`, and the matched
    unrelated passages for `remove_control`. Removal arms start with an empty
    replacement, which deletes the passage.
    """
    by_unit = {patient["unit"]: patient for patient in inventory}
    edits = []
    for unit in units:
        patient = by_unit[unit]
        if arm in ("flip", "reword", "hedge"):
            spans = [p for p in patient["passages"] if p["flip_edit"]]
        elif arm == "remove":
            spans = [p for p in patient["passages"] if p["removal_edit"]]
        elif arm == "remove_control":
            spans = patient["removal_controls"]
        else:
            raise ValueError(f"unknown arm: {arm}")
        text = reports[unit]["text"]
        for span in spans:
            original = text[span["start"] : span["end"]]
            edits.append(
                {
                    "unit": unit,
                    "start": span["start"],
                    "end": span["end"],
                    "kind": arm,
                    "category": span.get("category", "unrelated_control"),
                    "original_sha256": sha256(original),
                    "original": original,
                    "replacement": "",
                }
            )
    return edits


def check_edits(reports: dict[str, dict], edits: list[dict]) -> list[str]:
    """Return a list of problems with an edit spec (empty if it is usable)."""
    problems = []
    for i, edit in enumerate(edits):
        unit = edit["unit"]
        if unit not in reports:
            problems.append(f"edit {i}: {unit} is not in the report store")
            continue
        original = reports[unit]["text"][edit["start"] : edit["end"]]
        if sha256(original) != edit["original_sha256"]:
            problems.append(f"edit {i}: {unit} original text does not match its hash")
        keeps_text = edit["kind"] in ("flip", "reword", "hedge")
        if keeps_text and not edit["replacement"].strip():
            problems.append(f"edit {i}: {unit} {edit['kind']} has no replacement")
        if edit["replacement"] == original:
            problems.append(f"edit {i}: {unit} replacement is identical to original")
    for unit in {edit["unit"] for edit in edits}:
        spans = sorted((e["start"], e["end"]) for e in edits if e["unit"] == unit)
        for (_, end), (start, _) in zip(spans, spans[1:]):
            if start < end:
                problems.append(f"{unit}: two edits overlap")
    return problems


def apply_edits(text: str, edits: list[dict]) -> tuple[str, list[dict]]:
    """Apply one unit's edits and return the new text and where each landed.

    Edits are applied in order of position, tracking how far later offsets
    have moved, so each manifest row gives both the original and new offsets.
    """
    pieces = []
    manifest = []
    position = 0
    shift = 0
    for edit in sorted(edits, key=lambda e: e["start"]):
        pieces.append(text[position : edit["start"]])
        pieces.append(edit["replacement"])
        new_start = edit["start"] + shift
        new_end = new_start + len(edit["replacement"])
        manifest.append(
            {
                "unit": edit["unit"],
                "kind": edit["kind"],
                "category": edit.get("category", ""),
                "start": edit["start"],
                "end": edit["end"],
                "new_start": new_start,
                "new_end": new_end,
            }
        )
        shift += len(edit["replacement"]) - (edit["end"] - edit["start"])
        position = edit["end"]
    pieces.append(text[position:])
    return "".join(pieces), manifest


def write_arm(store_path: Path, edits: list[dict], out_dir: Path) -> dict[str, int]:
    """Write the edited store, roster, and manifest for one arm into `out_dir`.

    Only units with at least one edit are written. Every other field of each
    store row (`unit`, `document`, `metadata`) is copied unchanged. Refuses to
    overwrite an existing arm folder.
    """
    out_dir.mkdir(mode=0o750, parents=True, exist_ok=False)
    units = sorted({edit["unit"] for edit in edits})
    manifest = []
    with store_path.open() as source, (out_dir / store_path.name).open("w") as out:
        for line in source:
            row = json.loads(line)
            if row["unit"] not in units:
                continue
            mine = [edit for edit in edits if edit["unit"] == row["unit"]]
            row["text"], landed = apply_edits(row["text"], mine)
            for item in landed:
                item["document"] = row["document"]
            manifest.extend(landed)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (out_dir / "roster.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["unit"])
        writer.writerows([unit] for unit in units)
    (out_dir / "edits.json").write_text(json.dumps(manifest, indent=1))
    # Group-readable so teammates in __oncotrace can rerun the arm.
    for path in out_dir.iterdir():
        path.chmod(0o640)
    return {"units": len(units), "edits": len(manifest)}


ARMS = ["flip", "reword", "hedge", "remove", "remove_control"]


def main() -> None:
    """Run the `template` or `apply` step for one arm."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["template", "apply"])
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--units", nargs="+", help="patients (template step)")
    parser.add_argument("--reports", type=Path, default=REPORTS_PATH)
    parser.add_argument(
        "--inventory",
        type=Path,
        help="evidence_inventory.json from a results folder (template step)",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        default=SHARED_INPUTS,
        help="text-bearing specs and edited stores (outside Git)",
    )
    args = parser.parse_args()

    spec_path = args.inputs / f"edit_spec_{args.arm}.json"
    reports = load_reports(args.reports)

    if args.step == "template":
        if args.inventory is None or not args.units:
            parser.error("the template step needs --inventory and --units")
        if spec_path.exists():
            raise SystemExit(f"{spec_path} exists; delete it to start over")
        inventory = json.loads(args.inventory.read_text())
        edits = template_edits(reports, inventory, args.units, args.arm)
        spec_path.write_text(json.dumps(edits, indent=1, ensure_ascii=False))
        spec_path.chmod(0o640)
        print(f"wrote {len(edits)} edits for {len(args.units)} units to {spec_path}")
        return

    edits = json.loads(spec_path.read_text())
    problems = check_edits(reports, edits)
    if problems:
        raise SystemExit("not applied:\n" + "\n".join(problems))
    counts = write_arm(args.reports, edits, args.inputs / args.arm)
    print(f"{args.arm}: {counts['edits']} edits in {counts['units']} units written")

    # The roster and manifest are text-free; keep a copy with the experiment.
    # If a copy is already committed (you are rebuilding an arm), check that
    # the rebuild matches it instead.
    committed = EXPERIMENT_DIR / "inputs" / args.arm
    for name in ("roster.csv", "edits.json"):
        made = args.inputs / args.arm / name
        if not (committed / name).exists():
            committed.mkdir(parents=True, exist_ok=True)
            shutil.copy(made, committed / name)
            print(f"copied {name} to {committed}")
        # Compare lines, not bytes: Git may change the roster's line endings.
        elif (
            made.read_text().splitlines() == (committed / name).read_text().splitlines()
        ):
            print(f"{name} matches the committed copy in {committed}")
        else:
            print(f"WARNING: {name} differs from the committed copy in {committed}")


if __name__ == "__main__":
    main()
