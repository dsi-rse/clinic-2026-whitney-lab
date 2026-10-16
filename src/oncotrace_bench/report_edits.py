"""Make edited copies of reports for evidence-following experiments.

An edit spec is a JSON list of edits, written by a person, one per passage:

    {"unit": ..., "start": ..., "end": ..., "kind": "flip",
     "original_sha256": ..., "original": ..., "replacement": ...}

`start` and `end` are offsets into the ORIGINAL report. `original` is there
only so the person writing `replacement` can see what they are replacing;
`original_sha256` is what the script checks, so a spec made from a different
report version is refused. The spec holds protected text: keep it in the
private analysis folder.

Applying a spec writes a new report store holding only the edited units, a
roster for them, and a text-free manifest (`edits.json`) of where each edit
landed in the edited text. The original store is never written to.
"""

import csv
import hashlib
import json
from pathlib import Path


def sha256(text: str) -> str:
    """Return the sha256 hex digest of a string."""
    return hashlib.sha256(text.encode()).hexdigest()


def template_edits(
    reports: dict[str, dict], inventory: list[dict], units: list[str], arm: str
) -> list[dict]:
    """Return an edit spec with an empty `replacement` for each passage to edit.

    The passages come from the evidence inventory: those marked `flip_edit` for
    the `flip` and `reword` arms, `removal_edit` for `remove`, and the matched
    unrelated passages for `remove_control`. Removal arms start with an empty
    replacement, which deletes the passage.
    """
    by_unit = {patient["unit"]: patient for patient in inventory}
    edits = []
    for unit in units:
        patient = by_unit[unit]
        if arm in ("flip", "reword"):
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
        keeps_text = edit["kind"] in ("flip", "reword")
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
    out_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
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
    for path in out_dir.iterdir():
        path.chmod(0o600)
    return {"units": len(units), "edits": len(manifest)}
