"""Review the two rows where OncoTrace disagrees with a definite annotation (issue 26).

Issue 13 and PR 22 cover the rows where the *annotation* is undetermined. This
script covers the complement: the rows where the annotation gives a definite
value and the run still disagrees, so one side is wrong.

For each row in `inputs/rows.csv` it writes, from the four temperature runs:

- `run_answers.csv`     what each run answered, how it got there, and how much
                        of the report it read
- `evidence_spans.csv`  every citation the runs and the annotation made, as
                        character offsets, with a wording class for each span
- `report_vocabulary.csv`  how often each wording class occurs in the whole
                        report, and where, so "there is no number anywhere" is
                        a citable claim rather than an impression
- `measurements.csv`    every mm/cm measurement in the two reports, by offset
- `arithmetic.csv`      the candidate depth/thickness pairs worked out, so the
                        boundary claim can be checked
- `verdicts.csv`        the final table: annotation, four answers, four
                        confidences, earlier reading, verdict, deciding offsets
- `scope_check.csv`     every disagreement in all 50 patients and 4 runs,
                        grouped by annotation value, so the choice of two rows
                        can be checked rather than taken on trust
- `leak_check.csv`      a 7-word check that no report text reached these files

No report text is written. Spans are character offsets and wording classes.
Measurement values are written as numbers, the same way PR 18's
`audit_14_patients.csv` records `computed_percent`, because the boundary
arithmetic cannot be checked without them.

Example (from the repo root):

    PYTHONPATH=src python experiments/definite_disagreements/review_disagreements.py
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from oncotrace_bench.provenance import build
from oncotrace_bench.records import (
    ANNOTATIONS_DIR,
    covered_fraction,
    load_annotations,
    load_reports,
    load_run,
    read_windows,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
INPUTS_DIR = EXPERIMENT_DIR / "inputs"
DEFAULT_OUT = EXPERIMENT_DIR / "results"

# The four PR 21 runs: oncotrace fc3dadc, contract ba27b6ce, GLM-5.3-Flash.
# Group-readable by __oncotrace.
RUNS = Path("/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs")
DEFAULT_RUNS = {
    "t0": RUNS / "2026-10-23_temperature_t0",
    "t1_r1": RUNS / "2026-10-23_temperature_t1_r1",
    "t1_r2": RUNS / "2026-10-23_temperature_t1_r2",
    "t1_r3": RUNS / "2026-10-23_temperature_t1_r3",
}

# PR 21's per-patient table, the source of the four answers in issue 26's table.
DEFAULT_PATIENTS_CSV = (
    REPO_ROOT
    / "experiments"
    / "temperature"
    / "results"
    / "2026-10-25_152031"
    / "patients.csv"
)

# The citation groups an answer can carry, in the task contract's own order.
SPAN_GROUPS = ("depth_evidence", "quantified_depth", "counterevidence")

# The two fields the task contract scores, and the annotation value that hands a
# disagreement to issue 13 / PR 22 rather than to this issue.
SCORED_FIELDS = ("myometrial_invasion", "myometrial_invasion_percent")
UNDETERMINED = "cannot_be_determined"

# The answer fields that are enumerated labels, so safe to write out.
ANSWER_LABELS = (
    "myometrial_invasion",
    "myometrial_invasion_percent",
    "depth_basis",
    "confidence",
    "specimen_type",
    "adenomyosis_relation",
)

HALF = 50  # the percent boundary between the two depth labels
MM_PER_CM = 10

# Wording classes used to describe a span without quoting it.
#
# The vocabulary is the task contract's own
# (`tasks/endo_myometrial_invasion.yaml` names "full thickness", "transmural",
# "invades to serosa", "superficial half", "inner half"), not anything read off
# a report. Only the class name and a count are ever written out.
WORDING_CLASSES = {
    # Does the span say invasion happened at all?
    "invasion_word": r"invasi\w*|invad\w*",
    # The three kinds of wording the contract says DO settle a half. Kept apart
    # because "serosa" on its own is usually a gross surface description, and
    # only counts as full thickness next to an invasion word.
    "fraction_or_percent": (
        r"\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*(?:mm|cm)?\s*/\s*\d+|\d+\s+of\s+\d+"
    ),
    "half_word": r"\bhalf\b|\bthird\b|\bquarter\b|\binner\b|\bouter\b",
    "full_thickness_word": r"transmural|full[- ]thickness",
    "serosa_token": r"serosa",
    # Wording that states an extent without committing to a half. The contract
    # has no rule for this on its own -- that is the open question in issue 15.
    "unquantified_extent": r"superficial|minimal|focal|slight|early\b",
    # "confined to the endometrium", which points the other way.
    "confined_statement": r"confined",
    "negation": r"\b(no|not|without|free of|negative|absent)\b",
    "depth_statement": r"\bdepth\b",
    "thickness_statement": r"\bthickness\b",
    "myometrium_token": r"myometri\w*",
    "endometrium_token": r"endometri\w*",
    "gross_examination": r"gross",
    "staging_line": r"\bstage\b|\bfigo\b|pT1",
}

MEASUREMENT = re.compile(r"(\d+(?:\.\d+)?)\s*(mm|cm)\b", re.IGNORECASE)
PAGE_BREAK = re.compile(r"=====\s*PAGE\s*(\d+)\s*=====")

# How long a run of shared words counts as leaked report text.
SHINGLE_WORDS = 7
WORD = re.compile(r"[a-z0-9]+")


def parse_args() -> argparse.Namespace:
    """Read the command line."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument("--rows", type=Path, default=INPUTS_DIR / "rows.csv")
    parser.add_argument(
        "--patients-csv",
        type=Path,
        default=DEFAULT_PATIENTS_CSV,
        help="PR 21's per-patient table, used only for the scope check",
    )
    parser.add_argument("--verdicts", type=Path, default=INPUTS_DIR / "verdicts.csv")
    parser.add_argument(
        "--arithmetic", type=Path, default=INPUTS_DIR / "candidate_arithmetic.csv"
    )
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--label", default="")
    parser.add_argument(
        "--run",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="an OncoTrace run folder to read; repeat for each run",
    )
    args = parser.parse_args()
    if args.run:
        args.runs = dict(pair.split("=", 1) for pair in args.run)
        args.runs = {label: Path(path) for label, path in args.runs.items()}
    else:
        args.runs = DEFAULT_RUNS
    return args


def wording_classes(text: str) -> str:
    """Return the wording classes present in a passage, as a sorted string.

    Only class names leave this function, never the passage.
    """
    found = [
        name
        for name, pattern in WORDING_CLASSES.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]
    return " ".join(sorted(found))


def to_mm(value: float, unit: str) -> float:
    """Convert a measurement to millimetres."""
    return value * MM_PER_CM if unit.lower() == "cm" else value


def page_of(offset: int, text: str) -> int:
    """Return the page number an offset falls on, counting page-break markers."""
    page = 1
    for match in PAGE_BREAK.finditer(text):
        if match.start() > offset:
            break
        page = int(match.group(1))
    return page


def annotation_spans(annotation: dict) -> list[dict]:
    """Return the annotator's citations for one patient, as offsets only."""
    rows = []
    for field, content in annotation["fields"].items():
        for span in content.get("spans") or []:
            rows.append(
                {
                    "source": "annotation",
                    "group": field,
                    "document": span["document"],
                    "start": span["start"],
                    "end": span["end"],
                }
            )
    return rows


def run_spans(answer: dict) -> list[dict]:
    """Return one run's citations for one patient, as offsets only."""
    rows = []
    for group in SPAN_GROUPS:
        for span in answer.get(group) or []:
            rows.append(
                {
                    "group": group,
                    "document": span["document"],
                    "start": span["start"],
                    "end": span["end"],
                }
            )
    return rows


def refusal_signatures(record: dict) -> str:
    """Return the recoverable-error signatures a run hit, in order."""
    return " ".join(
        event.get("signature") or "unnamed"
        for event in record["events"]
        if event["kind"] == "recoverable_error"
    )


def truncated_replies(record: dict) -> int:
    """Count the model replies that were cut off at the token cap."""
    return sum(
        event["kind"] == "model_response" and event.get("finish_reason") == "length"
        for event in record["events"]
    )


def build_run_answers(
    patients: list[str], runs: dict[str, dict], reports: dict
) -> pd.DataFrame:
    """One row per patient and run: the answer, how it was reached, what was read."""
    rows = []
    for patient in patients:
        report = reports[patient]
        whole = {
            "document": report["document"],
            "start": 0,
            "end": len(report["text"]),
        }
        for label, run in runs.items():
            record = run[patient]
            answer = record["answer"]
            windows = read_windows(record)
            row = {"patient": patient, "run": label}
            row.update({name: answer.get(name) for name in ANSWER_LABELS})
            row.update(
                {
                    "model_calls": record["model_calls"],
                    "document_chars": record["document_chars"],
                    "doc_fraction_read": round(covered_fraction(whole, windows), 3),
                    "read_windows": len(windows),
                    "refusals": refusal_signatures(record),
                    "truncated_replies": truncated_replies(record),
                    "unresolved_conflicts_recorded": len(
                        answer.get("unresolved_conflicts") or []
                    ),
                }
            )
            row.update(
                {f"n_{group}": len(answer.get(group) or []) for group in SPAN_GROUPS}
            )
            rows.append(row)
    return pd.DataFrame(rows)


def build_evidence_spans(
    patients: list[str], runs: dict[str, dict], annotations: dict, reports: dict
) -> pd.DataFrame:
    """Every citation from the runs and the annotation, as offsets and classes."""
    rows = []
    for patient in patients:
        text = reports[patient]["text"]
        spans = annotation_spans(annotations[patient])
        for label, run in runs.items():
            for span in run_spans(run[patient]["answer"]):
                spans.append({"source": label, **span})
        for span in spans:
            passage = text[span["start"] : span["end"]]
            measurements = MEASUREMENT.findall(passage)
            rows.append(
                {
                    "patient": patient,
                    "source": span["source"],
                    "group": span["group"],
                    "start": span["start"],
                    "end": span["end"],
                    "chars": span["end"] - span["start"],
                    "page": page_of(span["start"], text),
                    "n_measurements": len(measurements),
                    "measurements_mm": " ".join(
                        str(round(to_mm(float(v), u), 2)) for v, u in measurements
                    ),
                    "wording_classes": wording_classes(passage),
                }
            )
    table = pd.DataFrame(rows)
    return table.sort_values(["patient", "start", "end", "source", "group"])


def build_report_vocabulary(patients: list[str], reports: dict) -> pd.DataFrame:
    """Count every wording class over each whole report, with its offsets.

    A zero count is the useful row: it shows a report never states a half, a
    fraction, or even the word "invasion", so a definite depth answer cannot
    have come from the text.
    """
    rows = []
    for patient in patients:
        text = reports[patient]["text"]
        for name, pattern in WORDING_CLASSES.items():
            starts = [m.start() for m in re.finditer(pattern, text, re.IGNORECASE)]
            rows.append(
                {
                    "patient": patient,
                    "wording_class": name,
                    "occurrences": len(starts),
                    "offsets": " ".join(str(s) for s in starts[:20]),
                    "pages": " ".join(sorted({str(page_of(s, text)) for s in starts})),
                }
            )
        rows.append(
            {
                "patient": patient,
                "wording_class": "measurement_mm_or_cm",
                "occurrences": len(MEASUREMENT.findall(text)),
                "offsets": "see measurements.csv",
                "pages": "",
            }
        )
    return pd.DataFrame(rows)


def build_measurements(patients: list[str], reports: dict) -> pd.DataFrame:
    """Every mm/cm measurement in each report, by offset and page."""
    rows = []
    for patient in patients:
        text = reports[patient]["text"]
        for match in MEASUREMENT.finditer(text):
            value, unit = float(match.group(1)), match.group(2).lower()
            # The 40 characters before a measurement name what it measures.
            lead_in = text[max(0, match.start() - 40) : match.start()]
            rows.append(
                {
                    "patient": patient,
                    "start": match.start(),
                    "end": match.end(),
                    "page": page_of(match.start(), text),
                    "value": value,
                    "unit": unit,
                    "value_mm": round(to_mm(value, unit), 2),
                    "lead_in_classes": wording_classes(lead_in),
                }
            )
    return pd.DataFrame(rows)


def build_arithmetic(candidates: pd.DataFrame, reports: dict) -> pd.DataFrame:
    """Work out each candidate depth-over-thickness pair and the label it gives."""
    rows = []
    for row in candidates.to_dict("records"):
        text = reports[row["patient"]]["text"]
        pairs = []
        for side in ("numerator", "denominator"):
            start, end = int(row[f"{side}_start"]), int(row[f"{side}_end"])
            found = MEASUREMENT.findall(text[start:end])
            if len(found) != 1:
                raise ValueError(
                    f"{row['patient']} {side} [{start}:{end}] holds "
                    f"{len(found)} measurements, expected 1"
                )
            pairs.append(to_mm(float(found[0][0]), found[0][1]))
        numerator, denominator = pairs
        percent = 100 * numerator / denominator
        rows.append(
            {
                "patient": row["patient"],
                "numerator_label": row["numerator_label"],
                "numerator_start": row["numerator_start"],
                "numerator_end": row["numerator_end"],
                "numerator_mm": numerator,
                "numerator_page": page_of(int(row["numerator_start"]), text),
                "denominator_label": row["denominator_label"],
                "denominator_start": row["denominator_start"],
                "denominator_end": row["denominator_end"],
                "denominator_mm": denominator,
                "denominator_page": page_of(int(row["denominator_start"]), text),
                "percent": round(percent, 1),
                "label_it_gives": (
                    "fifty_or_greater" if percent >= HALF else "less_than_50"
                ),
                "note": row["note"],
            }
        )
    return pd.DataFrame(rows)


VERDICT_VALUES = (
    "model wrong",
    "annotation wrong",
    "genuinely ambiguous",
    "task contract doesn't say",
)


def check_verdicts(verdicts: pd.DataFrame, spans: pd.DataFrame) -> None:
    """Fail early if a hand-written verdict is not one issue 26 allows.

    Also checks that every range named as deciding was really cited by somebody,
    so the judgement column cannot drift away from the evidence.
    """
    for row in verdicts.to_dict("records"):
        if row["verdict"] not in VERDICT_VALUES:
            raise ValueError(
                f"{row['patient']}: verdict {row['verdict']!r} is not one of "
                f"{VERDICT_VALUES}"
            )
        mine = spans[spans["patient"] == row["patient"]]
        cited = set(zip(mine["start"], mine["end"]))
        for offsets in str(row["deciding_offsets"]).split(";"):
            start, end = (int(part) for part in offsets.strip().split("-"))
            if (start, end) not in cited:
                raise ValueError(
                    f"{row['patient']}: deciding offsets {start}-{end} are not in "
                    "evidence_spans.csv, so nobody cited them"
                )


def build_verdicts(
    rows: pd.DataFrame,
    verdicts: pd.DataFrame,
    run_answers: pd.DataFrame,
    order: list[str],
) -> pd.DataFrame:
    """The issue 26 table: one row per patient and field, answers side by side."""
    judged = verdicts.set_index(["patient", "field"])
    table = []
    for row in rows.to_dict("records"):
        answers = run_answers[run_answers["patient"] == row["patient"]]
        answers = answers.set_index("run")
        table.append(
            {
                "patient": row["patient"],
                "field": row["field"],
                "annotation": row["annotation"],
                "run_answers": " / ".join(answers.loc[r, row["field"]] for r in order),
                "run_confidences": " / ".join(
                    answers.loc[r, "confidence"] for r in order
                ),
                "run_depth_basis": " / ".join(
                    answers.loc[r, "depth_basis"] for r in order
                ),
                "runs_agreeing_with_annotation": int(
                    sum(
                        answers.loc[r, row["field"]] == row["annotation"] for r in order
                    )
                ),
                "earlier_reading": row["earlier_reading"],
                "earlier_reading_source": row["earlier_reading_source"],
                **{
                    name: judged.loc[(row["patient"], row["field"]), name]
                    for name in judged.columns
                },
            }
        )
    return pd.DataFrame(table)


def build_scope_check(patients_csv: Path) -> pd.DataFrame:
    """Group every disagreement in PR 21's 200 patient-runs by annotation value.

    Issue 26 takes the rows whose annotation is not `cannot_be_determined`; the
    rest belong to issue 13 / PR 22. This table shows the whole split, so the
    choice of two rows can be checked instead of taken on trust.
    """
    table = pd.read_csv(patients_csv)
    rows = []
    for field in SCORED_FIELDS:
        wrong = table[~table[f"agree_{field}"]]
        grouped = wrong.groupby([f"ann_{field}", f"run_{field}"])
        for (annotation, answered), group in grouped:
            rows.append(
                {
                    "field": field,
                    "annotation": annotation,
                    "run_answer": answered,
                    "run_rows": len(group),
                    "patients": " ".join(sorted(set(group["unit"]))),
                    "owner": (
                        "issue 13 / PR 22"
                        if annotation == UNDETERMINED
                        else "issue 26 (this folder)"
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(["field", "annotation", "run_answer"])


def shingles(text: str) -> set[tuple[str, ...]]:
    """Return the runs of SHINGLE_WORDS consecutive words in a passage."""
    words = WORD.findall(text.lower())
    return {
        tuple(words[i : i + SHINGLE_WORDS])
        for i in range(len(words) - SHINGLE_WORDS + 1)
    }


def build_leak_check(folder: Path, reports: dict) -> pd.DataFrame:
    """Check that no file in a folder shares a long run of words with a report."""
    report_shingles = set()
    for report in reports.values():
        report_shingles |= shingles(report["text"])
    rows = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        hits = shingles(path.read_text(errors="replace")) & report_shingles
        rows.append(
            {
                "file": str(path.relative_to(folder)),
                "shared_word_runs": len(hits),
                "clean": not hits,
            }
        )
    return pd.DataFrame(rows)


def write_summary(
    path: Path, tables: dict[str, pd.DataFrame], order: list[str]
) -> None:
    """Write the numbers the write-up quotes, so each one has a committed source."""
    verdicts, run_answers = tables["verdicts.csv"], tables["run_answers.csv"]
    lines = [
        f"runs compared, in order: {', '.join(order)}",
        f"rows in scope: {len(verdicts)}",
        "",
        "== the two rows ==",
        verdicts[
            [
                "patient",
                "annotation",
                "run_answers",
                "run_confidences",
                "runs_agreeing_with_annotation",
                "verdict",
                "failure_mode",
                "deciding_offsets",
            ]
        ].to_string(index=False),
        "",
        "== depth_basis each run claimed, for the same report ==",
        verdicts[["patient", "run_depth_basis"]].to_string(index=False),
        "",
        "== how each run got there ==",
        run_answers[
            [
                "patient",
                "run",
                "myometrial_invasion",
                "myometrial_invasion_percent",
                "confidence",
                "depth_basis",
                "model_calls",
                "doc_fraction_read",
                "truncated_replies",
                "refusals",
                "unresolved_conflicts_recorded",
                "n_quantified_depth",
                "n_counterevidence",
            ]
        ].to_string(index=False),
        "",
        "== boundary arithmetic ==",
        tables["arithmetic.csv"].to_string(index=False),
        "",
        "== scope check: every disagreement in PR 21's 200 patient-runs ==",
        tables["scope_check.csv"].to_string(index=False),
        "",
        f"leak check ({SHINGLE_WORDS}-word runs against the two reports): "
        "see leak_check.csv",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    """Build every table and write one results folder."""
    args = parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = args.results_dir / (f"{stamp}_{args.label}" if args.label else stamp)

    rows = pd.read_csv(args.rows)
    # Blank judgement cells are meaningful ("no failure mode, the model is not
    # being blamed"), so keep them as empty strings rather than NaN.
    verdicts = pd.read_csv(args.verdicts).fillna("")
    candidates = pd.read_csv(args.arithmetic)
    patients = list(rows["patient"])
    order = list(args.runs)

    annotations = load_annotations(args.annotations)
    all_reports = load_reports()
    reports = {unit: all_reports[unit] for unit in patients}
    runs = {label: load_run(folder) for label, folder in args.runs.items()}

    run_answers = build_run_answers(patients, runs, reports)
    spans = build_evidence_spans(patients, runs, annotations, reports)
    check_verdicts(verdicts, spans)
    tables = {
        "verdicts.csv": build_verdicts(rows, verdicts, run_answers, order),
        "run_answers.csv": run_answers,
        "evidence_spans.csv": spans,
        "report_vocabulary.csv": build_report_vocabulary(patients, reports),
        "measurements.csv": build_measurements(patients, reports),
        "arithmetic.csv": build_arithmetic(candidates, reports),
        "scope_check.csv": build_scope_check(args.patients_csv),
    }

    # Record provenance before writing anything, so the new folder is not
    # listed as an uncommitted file.
    prov = build(
        inputs={
            "rows": args.rows,
            "verdicts": args.verdicts,
            "candidate_arithmetic": args.arithmetic,
            "pr21_patients": args.patients_csv,
        },
        runs=args.runs,
        repo_root=REPO_ROOT,
        command=" ".join(sys.argv),
        patients=patients,
        annotations={"path": str(args.annotations), "files": len(annotations)},
    )

    out.mkdir(parents=True)
    for name, table in tables.items():
        table.to_csv(out / name, index=False)
        print(f"{name}: {len(table)} rows")
    (out / "provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
    write_summary(out / "summary.txt", tables, order)
    # The leak check runs last, over every file already written.
    leak = build_leak_check(out, reports)
    leak.to_csv(out / "leak_check.csv", index=False)
    print(f"{int(leak['clean'].sum())} of {len(leak)} files clean in the leak check")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
