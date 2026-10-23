"""Build the annotation-only tables for the unresolved_conflicts investigation.

Reads Mariam's annotations for `endo_myometrial_invasion` and writes CSVs with
values, counts and computed percents only. No report text is written.

Example:
    python experiments/unresolved_conflicts/annotation_tables.py
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
DEFAULT_ANNOTATIONS = REPO_ROOT / "annotations" / "endo_myometrial_invasion"
DEFAULT_OUT = EXPERIMENT_DIR / "results"

# "12.0 of 26.0 mm", "0.5/1.4", "2.0 cm into a 2.2 cm", "5/15"
FRACTION = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:mm|cm)?\s*(?:/|of|into)\s*(?:a\s+)?(\d+(?:\.\d+)?)"
)
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
# "less than 50%" is a threshold, not a measured percent
THRESHOLD = re.compile(
    r"(?:less than|under|below|greater than|more than|over|at least|up to"
    r"|[<>\u2264\u2265]=?)\s*\d+(?:\.\d+)?\s*%",
    re.IGNORECASE,
)

HALF = 50  # percent threshold between the two labels

# (presence, percent) pairs that make sense together
CONSISTENT = {
    ("present", "less_than_50"),
    ("present", "fifty_or_greater"),
    ("not_identified", "not_applicable"),
    ("cannot_be_determined", "not_applicable"),
    ("cannot_be_determined", "cannot_be_determined"),
    ("present", "cannot_be_determined"),  # present, but no usable percent
}


def bucket(percent: float) -> str:
    """Return the percent label for a number."""
    return "fifty_or_greater" if percent >= HALF else "less_than_50"


def span_text(fields: dict) -> str:
    """Join the evidence text from the three invasion-related fields."""
    names = ("myometrial_invasion", "myometrial_invasion_percent", "depth_basis")
    return " ".join(s["text"] for n in names for s in fields[n]["spans"])


def computed_percents(text: str) -> list[float]:
    """Percents stated in the text, or worked out from fractions like 5/15."""
    stated = [float(p) for p in PERCENT.findall(THRESHOLD.sub("", text))]
    fractions = [
        100 * float(a) / float(b)
        for a, b in FRACTION.findall(text)
        if 0 < float(b) and float(a) <= float(b)
    ]
    return [round(p) for p in stated + fractions]


def read_annotations(folder: Path) -> pd.DataFrame:
    """One row per patient: values, note flag, and numbers found in the evidence."""
    rows = []
    for path in sorted(folder.glob("*.json")):
        fields = json.loads(path.read_text())["fields"]
        percents = computed_percents(span_text(fields))
        note = fields["unresolved_conflicts"]["value"] or ""
        rows.append(
            {
                "patient": path.stem,
                "invasion": fields["myometrial_invasion"]["value"],
                "percent": fields["myometrial_invasion_percent"]["value"],
                "depth_basis": fields["depth_basis"]["value"],
                "adenomyosis": fields["adenomyosis_relation"]["value"],
                "has_note": bool(note.strip()),
                "n_percents_found": len(percents),
                "percents_found": ";".join(str(p) for p in percents),
                "worst_case_bucket": bucket(max(percents)) if percents else "",
            }
        )
    return pd.DataFrame(rows)


def percent_check(overview: pd.DataFrame) -> pd.DataFrame:
    """Task 5: patients where a number was found, and whether her percent matches."""
    found = overview[overview["n_percents_found"] > 0].copy()
    found["matches_worst_case"] = found["percent"] == found["worst_case_bucket"]
    columns = [
        "patient",
        "percents_found",
        "worst_case_bucket",
        "percent",
        "matches_worst_case",
        "has_note",
    ]
    return found[columns]


def presence_vs_percent(overview: pd.DataFrame) -> pd.DataFrame:
    """Task 3: patients whose presence and percent labels do not fit together."""
    pairs = zip(overview["invasion"], overview["percent"])
    fits = [pair in CONSISTENT for pair in pairs]
    return overview.loc[[not f for f in fits], ["patient", "invasion", "percent"]]


def cannot_be_determined_breakdown(overview: pd.DataFrame) -> pd.DataFrame:
    """Task 4: split the cannot_be_determined percents by how much evidence exists.

    `none_stated` means no percentage or fraction was given. A fraction or
    percentage in the evidence means the number existed but was not used.
    Real conflicts have to be confirmed by hand in the audit.
    """
    cbd = overview[overview["percent"] == "cannot_be_determined"]
    return (
        cbd.groupby(["depth_basis", "n_percents_found"])
        .agg(patients=("patient", "count"), ids=("patient", ", ".join))
        .reset_index()
    )


def main() -> None:
    """Write the tables."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    overview = read_annotations(args.annotations)
    args.out.mkdir(parents=True, exist_ok=True)
    tables = {
        "annotation_overview.csv": overview,
        "percent_check.csv": percent_check(overview),
        "presence_vs_percent.csv": presence_vs_percent(overview),
        "cannot_be_determined_breakdown.csv": cannot_be_determined_breakdown(overview),
    }
    for name, table in tables.items():
        table.to_csv(args.out / name, index=False)
        print(f"{name}: {len(table)} rows")
    print(f"{overview['has_note'].sum()} of {len(overview)} patients have a note")


if __name__ == "__main__":
    main()
