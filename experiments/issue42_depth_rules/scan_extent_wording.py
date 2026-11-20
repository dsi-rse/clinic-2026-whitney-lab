"""Find every report whose depth wording looks like TCGA-A5-A0GJ's (issue #42).

A0GJ's only depth statement places the tumour in the superficial myometrium
without a number, a half, or the word "invasion". Before changing the contract
for that wording, issue #42 asks which other patients the change would touch.

The script splits each report into statements (lines, bullets and sentences)
and keeps every statement that mentions the myometrium. Each kept statement
gets the wording classes it contains and one of these types:

- `extent_no_invasion_word`: A0GJ's type. Extent wording ("superficial",
  "minimal", ...) and no invasion word, half, number, depth or thickness.
- `extent_with_invasion_word`: extent wording and an invasion word, but no
  half, number, depth or thickness ("superficial invasion", say).
- `other`: anything else.

A patient is in group `extent_only_report` when they have an
`extent_no_invasion_word` statement and no other myometrium statement that
could settle depth (A0GJ's whole-report pattern), and in
`extent_with_other_depth_wording` when they have one but another statement
might settle it.

Writes, with patient IDs, offsets, classes and labels only (no report text):

- `extent_statements.csv`  every myometrium statement of the two extent types
- `extent_patients.csv`    every patient with at least one such statement, with
                           the annotation's labels where one exists
- `scan_summary.csv`       patient counts per group and statement type
- `annotator_labels.csv`   for annotated patients with a "superficial" extent
                           statement, how the annotator labelled depth

Run from the repo root:

    PYTHONPATH=src python experiments/issue42_depth_rules/scan_extent_wording.py \
        --reports data/endometrial/documents/ucec_pathology_report.jsonl
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from oncotrace_bench.provenance import build
from oncotrace_bench.records import ANNOTATIONS_DIR, load_annotations, load_reports

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
DEFAULT_REPORTS = REPO_ROOT / "data/endometrial/documents/ucec_pathology_report.jsonl"

# Wording classes. Most are copied from #26's
# experiments/definite_disagreements/review_disagreements.py so the two
# experiments use the same words. New here: "infiltrat" as an invasion word,
# "serosa" counted as full thickness, a plain measurement, and "superficial"
# split out of the extent words because the new contract names it.
CLASSES = {
    "invasion_word": r"invasi\w*|invad\w*|infiltrat\w*",
    "half_word": r"\bhalf\b|\bthird\b|\bquarter\b|\binner\b|\bouter\b",
    "full_thickness_word": r"transmural|full[- ]thickness|serosa",
    "fraction_or_percent": (
        r"\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*(?:mm|cm)?\s*/\s*\d+|\d+\s+of\s+\d+"
    ),
    "measurement": r"\d+(?:\.\d+)?\s*(?:mm|cm)\b",
    "depth_statement": r"\bdepth\b",
    "thickness_statement": r"\bthickness\b",
    "superficial_word": r"superficial\w*",
    "unquantified_extent": r"superficial\w*|minimal\w*|focal\w*|slight\w*|early\b",
    "confined_statement": r"confined",
    "negation": r"\b(?:no|not|without|free of|negative|absent)\b",
}
PATTERNS = {name: re.compile(p, re.IGNORECASE) for name, p in CLASSES.items()}
MYOMETRIUM = re.compile(r"myometri\w*", re.IGNORECASE)

# Classes that, next to a myometrium mention, can settle the half on their own.
SETTLING = (
    "half_word",
    "full_thickness_word",
    "fraction_or_percent",
    "measurement",
    "depth_statement",
    "thickness_statement",
)
EXTENT_TYPES = ("extent_no_invasion_word", "extent_with_invasion_word")
GROUPS = ("extent_only_report", "extent_with_other_depth_wording")

# A statement ends at a blank line, a bullet line ("-" alone), a page marker,
# or a full stop / semicolon followed by space.
STATEMENT_BREAK = re.compile(r"\n\s*-\s*\n|\n\s*\n|=====[^=]*=====|(?<=[.;])\s+")


def statements(text: str) -> list[tuple[int, int]]:
    """Return (start, end) offsets of each statement in a report."""
    spans, start = [], 0
    for brk in STATEMENT_BREAK.finditer(text):
        if brk.start() > start:
            spans.append((start, brk.start()))
        start = brk.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def statement_type(found: list[str]) -> str:
    """Return a myometrium statement's type from the classes it contains."""
    if "unquantified_extent" not in found or any(n in found for n in SETTLING):
        return "other"
    if "invasion_word" in found:
        return "extent_with_invasion_word"
    return "extent_no_invasion_word"


def scan_report(unit: str, text: str) -> list[dict]:
    """Return one row per statement in a report that mentions the myometrium."""
    rows = []
    for start, end in statements(text):
        passage = text[start:end]
        if not MYOMETRIUM.search(passage):
            continue
        found = [name for name, p in PATTERNS.items() if p.search(passage)]
        rows.append(
            {
                "patient": unit,
                "start": start,
                "end": end,
                "page": text.count("===== PAGE", 0, start),
                "type": statement_type(found),
                "classes": " ".join(found),
            }
        )
    return rows


def patient_group(rows: list[dict]) -> str:
    """Return the patient's group (see the module docstring)."""
    if not any(row["type"] == "extent_no_invasion_word" for row in rows):
        return "other"
    settling = ("invasion_word", *SETTLING)
    if any(name in row["classes"].split() for row in rows for name in settling):
        return "extent_with_other_depth_wording"
    return "extent_only_report"


def annotation_labels(annotation: dict | None) -> dict:
    """Return the annotation's invasion, depth and depth-basis values, or blanks."""
    if annotation is None:
        return {"annotated": False, "ann_invasion": "", "ann_percent": ""}
    fields = annotation["fields"]
    return {
        "annotated": True,
        "ann_invasion": fields["myometrial_invasion"]["value"],
        "ann_percent": fields["myometrial_invasion_percent"]["value"],
        "ann_basis": fields["depth_basis"]["value"],
    }


def offsets(rows: list[dict], kind: str, superficial: bool = False) -> str:
    """Return the offsets of a patient's statements of one type, space-separated."""
    return " ".join(
        f"{r['start']}-{r['end']}"
        for r in rows
        if r["type"] == kind and (not superficial or "superficial_word" in r["classes"])
    )


def parse_args() -> argparse.Namespace:
    """Read the command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument("--out", type=Path, default=EXPERIMENT_DIR / "results")
    parser.add_argument("--label", default="extent_scan")
    return parser.parse_args()


def main() -> None:
    """Scan every report and write the tables."""
    args = parse_args()
    reports = load_reports(args.reports)
    annotations = load_annotations(args.annotations)

    statement_rows, patient_rows = [], []
    for unit in sorted(reports):
        rows = scan_report(unit, reports[unit]["text"])
        extent_rows = [row for row in rows if row["type"] in EXTENT_TYPES]
        if not extent_rows:
            continue
        statement_rows += extent_rows
        patient_rows.append(
            {
                "patient": unit,
                "group": patient_group(rows),
                **{kind: offsets(rows, kind) for kind in EXTENT_TYPES},
                "superficial_with_invasion_word": offsets(
                    rows, "extent_with_invasion_word", superficial=True
                ),
                "superficial_no_invasion_word": offsets(
                    rows, "extent_no_invasion_word", superficial=True
                ),
                "myometrium_statements": len(rows),
                **annotation_labels(annotations.get(unit)),
            }
        )
    patients = pd.DataFrame(patient_rows).fillna("")

    def count(mask: pd.Series) -> dict:
        return {
            "patients": int(mask.sum()),
            "annotated": int((mask & patients["annotated"]).sum()),
        }

    summary = pd.DataFrame(
        [{"group_or_type": g, **count(patients["group"] == g)} for g in GROUPS]
        + [{"group_or_type": k, **count(patients[k] != "")} for k in EXTENT_TYPES]
        + [
            {"group_or_type": k, **count(patients[k] != "")}
            for k in ("superficial_no_invasion_word", "superficial_with_invasion_word")
        ]
        + [
            {
                "group_or_type": "all_reports",
                "patients": len(reports),
                "annotated": len(annotations),
            }
        ]
    )

    # How the annotator labelled depth where a "superficial" extent statement
    # exists, split by whether that statement has an invasion word.
    label_rows = []
    for kind in ("superficial_no_invasion_word", "superficial_with_invasion_word"):
        chosen = patients[(patients[kind] != "") & patients["annotated"]]
        for (invasion, percent), n in (
            chosen.groupby(["ann_invasion", "ann_percent"]).size().items()
        ):
            label_rows.append(
                {
                    "statement_type": kind,
                    "ann_invasion": invasion,
                    "ann_percent": percent,
                    "patients": n,
                    "patient_ids": " ".join(
                        chosen[
                            (chosen["ann_invasion"] == invasion)
                            & (chosen["ann_percent"] == percent)
                        ]["patient"]
                    ),
                }
            )

    record = build(
        inputs={"reports": args.reports},
        runs={},
        repo_root=REPO_ROOT,
        script=str(Path(__file__).relative_to(REPO_ROOT)),
        command=" ".join(sys.argv),
        annotations_dir=str(args.annotations),
        annotation_files=len(annotations),
    )
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = args.out / f"{stamp}_{args.label}"
    out.mkdir(parents=True)
    pd.DataFrame(statement_rows).to_csv(out / "extent_statements.csv", index=False)
    patients.to_csv(out / "extent_patients.csv", index=False)
    summary.to_csv(out / "scan_summary.csv", index=False)
    pd.DataFrame(label_rows).to_csv(out / "annotator_labels.csv", index=False)
    (out / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(summary.to_string(index=False))
    print(pd.DataFrame(label_rows).to_string(index=False))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
