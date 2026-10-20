"""Compare an OncoTrace run's answers and citations with human annotations.

Three questions, per patient:

1. Does the run give the same field values as the annotator?
2. Does the run cite the passages the annotator marked as decisive, or
   other passages?
3. Had the model actually been shown the decisive passages (by `read`
   calls) before it submitted its answer?

Writes three text-free CSV files (IDs, offsets, labels, numbers only):

- alignment_annotated.csv: one row per annotated patient (field agreement,
  citation alignment, what was read before answering).
- alignment_spans.csv: one row per annotated span and per run citation.
- reading_coverage_run.csv: one row per run record (all patients).

Then prints a short summary. Called by run_experiment.py.
"""

from pathlib import Path

import pandas as pd

from oncotrace_bench.records import (
    covered_fraction,
    overlap,
    read_windows,
)

# Fields compared between the run answer and the annotation.
ANSWER_FIELDS = (
    "myometrial_invasion",
    "myometrial_invasion_percent",
    "depth_basis",
    "specimen_type",
    "adenomyosis_relation",
)

# Annotated fields whose spans are the "decisive passage" for depth.
DECISIVE_FIELDS = (
    "myometrial_invasion",
    "myometrial_invasion_percent",
    "depth_basis",
)

# Run citation groups that make the depth claim.
# (quantified_depth is required to be a subset of depth_evidence.)
RUN_DEPTH_GROUPS = ("depth_evidence", "quantified_depth")

# All run citation groups, for the per-span table.
RUN_CITATION_GROUPS = (
    "depth_evidence",
    "quantified_depth",
    "counterevidence",
    "specimen_evidence",
)


def as_span(span: dict) -> dict:
    """Return just the document and offsets of a span (drops any text)."""
    return {"document": span["document"], "start": span["start"], "end": span["end"]}


def unique_spans(spans: list[dict]) -> list[dict]:
    """Return spans with exact duplicates (same document and offsets) removed."""
    seen = set()
    result = []
    for span in spans:
        key = (span["document"], span["start"], span["end"])
        if key not in seen:
            seen.add(key)
            result.append(as_span(span))
    return result


def annotated_spans(annotation: dict, fields: tuple[str, ...]) -> list[dict]:
    """Return the unique annotated spans across the given fields."""
    spans = []
    for field in fields:
        spans.extend(annotation["fields"][field]["spans"])
    return unique_spans(spans)


def run_spans(answer: dict, groups: tuple[str, ...]) -> list[dict]:
    """Return the unique run citation spans across the given citation groups."""
    spans = []
    for group in groups:
        spans.extend(answer.get(group, []))
    return unique_spans(spans)


def touches_any(span: dict, others: list[dict]) -> bool:
    """Return True if `span` shares at least one character with any of `others`."""
    return any(overlap(span, other) > 0 for other in others)


def decision_sequence(record: dict) -> int | None:
    """Return the sequence number of the model response that made the accepted submit.

    Reads with a smaller sequence number had already been shown to the model
    when it wrote its answer. Rejected submits are logged as
    `recoverable_error` events, so the single `submit` event is the accepted
    one. Returns None for no-answer records, meaning "use every read".
    """
    events = record["events"]
    submit = next((e["sequence"] for e in events if e["kind"] == "submit"), None)
    if submit is None:
        return None
    responses = [
        e["sequence"]
        for e in events
        if e["kind"] == "model_response" and e["sequence"] < submit
    ]
    return responses[-1]


def first_submit_sequence(record: dict) -> int | None:
    """Return the sequence number of the first model response that tried to submit."""
    for event in record["events"]:
        if event["kind"] == "model_response" and "submit" in event["called_tools"]:
            return event["sequence"]
    return None


def fraction_of_document_read(
    record: dict, document: str, before_sequence: int | None
) -> float:
    """Return the fraction of the document's characters shown by reads before a point.

    If `before_sequence` is None, every read in the record is counted.
    """
    whole_document = {"document": document, "start": 0, "end": record["document_chars"]}
    return covered_fraction(whole_document, read_windows(record, before_sequence))


def count_events(record: dict, kind: str) -> int:
    """Return how many events of one kind a record has."""
    return sum(1 for event in record["events"] if event["kind"] == kind)


def count_rejected_submits(record: dict) -> int:
    """Return how many submit attempts were rejected by the contract checks."""
    return sum(
        1
        for event in record["events"]
        if event["kind"] == "recoverable_error" and event["tool"] == "submit"
    )


def coverage_row(unit: str, record: dict, document: str) -> dict:
    """Return one row of reading-coverage numbers for any run record."""
    answer = record["answer"]
    answered = answer["status"] == "answered"
    first_submit = first_submit_sequence(record)
    return {
        "unit": unit,
        "status": answer["status"],
        "myometrial_invasion": answer.get("myometrial_invasion"),
        "myometrial_invasion_percent": answer.get("myometrial_invasion_percent"),
        "document_chars": record["document_chars"],
        "frac_read_before_first_submit": (
            fraction_of_document_read(record, document, first_submit)
            if first_submit is not None
            else None
        ),
        "frac_read_before_decision": (
            fraction_of_document_read(record, document, decision_sequence(record))
            if answered
            else None
        ),
        "frac_read_total": fraction_of_document_read(record, document, None),
        "n_reads": count_events(record, "read"),
        "n_searches": count_events(record, "search"),
        "n_submit_attempts": count_rejected_submits(record) + int(answered),
        "model_calls": record["model_calls"],
    }


def annotated_row(unit: str, record: dict, annotation: dict, document: str) -> dict:
    """Return one row comparing a run record with its annotation."""
    answer = record["answer"]
    answered = answer["status"] == "answered"
    row = {"unit": unit, "run_status": answer["status"]}

    # 1. Field-by-field agreement (left blank when the run gave no answer).
    for field in ANSWER_FIELDS:
        annotated_value = annotation["fields"][field]["value"]
        run_value = answer.get(field)
        row[f"ann_{field}"] = annotated_value
        row[f"run_{field}"] = run_value
        row[f"agree_{field}"] = run_value == annotated_value if answered else None

    decisive = annotated_spans(annotation, DECISIVE_FIELDS)
    any_annotated = annotated_spans(annotation, tuple(annotation["fields"]))
    run_depth = run_spans(answer, RUN_DEPTH_GROUPS)
    depth_evidence = run_spans(answer, ("depth_evidence",))
    counterevidence = run_spans(answer, ("counterevidence",))

    # 2. Citation alignment, in both directions.
    n_decisive_cited = sum(touches_any(span, run_depth) for span in decisive)
    n_run_on_decisive = sum(touches_any(span, decisive) for span in depth_evidence)
    n_run_on_any = sum(touches_any(span, any_annotated) for span in depth_evidence)
    row["n_ann_decisive_spans"] = len(decisive)
    row["n_ann_decisive_cited"] = n_decisive_cited
    row["frac_ann_decisive_cited"] = (
        n_decisive_cited / len(decisive) if decisive else None
    )
    row["n_ann_decisive_in_run_counterevidence"] = sum(
        touches_any(span, counterevidence) for span in decisive
    )
    row["n_run_depth_evidence"] = len(depth_evidence)
    row["n_run_depth_on_ann_decisive"] = n_run_on_decisive
    row["n_run_depth_on_any_ann"] = n_run_on_any
    row["n_run_depth_elsewhere"] = len(depth_evidence) - n_run_on_any
    row["no_shared_passage"] = answered and n_decisive_cited == 0

    # 3. What had the model been shown before it answered?
    decided_at = decision_sequence(record)
    shown = read_windows(record, decided_at)
    read_fractions = [covered_fraction(span, shown) for span in decisive]
    row["min_frac_decisive_read"] = min(read_fractions, default=None)
    row["n_decisive_fully_read"] = sum(f == 1.0 for f in read_fractions)
    row["n_decisive_unread"] = sum(f == 0.0 for f in read_fractions)
    first_submit = first_submit_sequence(record)
    row["frac_doc_read_before_first_submit"] = (
        fraction_of_document_read(record, document, first_submit)
        if first_submit is not None
        else None
    )
    row["frac_doc_read_before_decision"] = fraction_of_document_read(
        record, document, decided_at
    )

    # 4. Citation counts.
    row["n_counterevidence"] = len(counterevidence)
    row["cited_counterevidence"] = len(counterevidence) > 0
    row["n_reads"] = count_events(record, "read")
    row["n_searches"] = count_events(record, "search")
    row["n_rejected_submits"] = count_rejected_submits(record)
    row["model_calls"] = record["model_calls"]
    return row


def span_rows(unit: str, record: dict, annotation: dict) -> list[dict]:
    """Return one row per annotated span and per run citation, as offsets only.

    Annotated spans get how much of them the run's depth citations (and
    counterevidence) cover; run citations get how much of them the
    annotated spans cover. Both get how much the model had read before
    deciding.
    """
    answer = record["answer"]
    decisive = annotated_spans(annotation, DECISIVE_FIELDS)
    any_annotated = annotated_spans(annotation, tuple(annotation["fields"]))
    run_depth = run_spans(answer, RUN_DEPTH_GROUPS)
    counterevidence = run_spans(answer, ("counterevidence",))
    shown = read_windows(record, decision_sequence(record))

    rows = []
    for field, value in annotation["fields"].items():
        for span in value["spans"]:
            rows.append(
                {
                    "unit": unit,
                    "side": "annotation",
                    "group": field,
                    "start": span["start"],
                    "end": span["end"],
                    "covered_by_run_depth": covered_fraction(span, run_depth),
                    "covered_by_run_counterevidence": covered_fraction(
                        span, counterevidence
                    ),
                    "covered_by_ann_decisive": None,
                    "covered_by_ann_any": None,
                    "frac_read_before_decision": covered_fraction(span, shown),
                }
            )
    for group in RUN_CITATION_GROUPS:
        for span in answer.get(group, []):
            rows.append(
                {
                    "unit": unit,
                    "side": "run",
                    "group": group,
                    "start": span["start"],
                    "end": span["end"],
                    "covered_by_run_depth": None,
                    "covered_by_run_counterevidence": None,
                    "covered_by_ann_decisive": covered_fraction(span, decisive),
                    "covered_by_ann_any": covered_fraction(span, any_annotated),
                    "frac_read_before_decision": covered_fraction(span, shown),
                }
            )
    return rows


# Treat a document as "read in full" at or above this fraction.
FULL_READ = 0.99


def ids(table: pd.DataFrame) -> str:
    """Return the unit IDs of a table as one comma-separated string."""
    return ", ".join(table["unit"]) if len(table) else "(none)"


def print_agreement(annotated: pd.DataFrame) -> None:
    """Print field-level agreement next to an always-the-majority baseline."""
    answered = annotated[annotated["run_status"] == "answered"]
    print(f"\n## Field agreement ({len(answered)} answered of {len(annotated)})")
    rows = []
    for field in ANSWER_FIELDS:
        majority_value = annotated[f"ann_{field}"].value_counts().idxmax()
        rows.append(
            {
                "field": field,
                "agree": int(answered[f"agree_{field}"].sum()),
                "of": len(answered),
                "majority_value": majority_value,
                "majority_baseline": int(
                    (answered[f"ann_{field}"] == majority_value).sum()
                ),
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))

    present = answered[answered["ann_myometrial_invasion"] == "present"]
    print(
        f"\nPercent field where annotation label is present: "
        f"{int(present['agree_myometrial_invasion_percent'].sum())}/{len(present)}"
    )
    print("\nPercent field, annotation (rows) vs run (columns):")
    print(
        pd.crosstab(
            annotated["ann_myometrial_invasion_percent"],
            annotated["run_myometrial_invasion_percent"].fillna("(no answer)"),
        ).to_string()
    )
    wrong = answered[~answered["agree_myometrial_invasion_percent"].astype(bool)]
    print(f"Percent disagreements: {ids(wrong)}")


def print_citations(annotated: pd.DataFrame) -> None:
    """Print how often the run cites the annotated decisive passages."""
    answered = annotated[annotated["run_status"] == "answered"]
    cites_all = answered[answered["frac_ann_decisive_cited"] == 1.0]
    cites_some = answered[answered["n_ann_decisive_cited"] > 0]
    disjoint = answered[answered["no_shared_passage"].astype(bool)]
    elsewhere = answered[answered["n_run_depth_elsewhere"] > 0]
    in_counter = answered[answered["n_ann_decisive_in_run_counterevidence"] > 0]
    n = len(answered)
    print("\n## Citation alignment (run depth_evidence/quantified_depth)")
    print(f"Cites every annotated decisive span: {len(cites_all)}/{n}")
    print(f"Cites at least one annotated decisive span: {len(cites_some)}/{n}")
    print(f"Cites none of them (entirely different passages): {ids(disjoint)}")
    print(
        f"Has depth_evidence touching no annotated span of any field: "
        f"{len(elsewhere)}/{n} patients, "
        f"{int(answered['n_run_depth_elsewhere'].sum())} of "
        f"{int(answered['n_run_depth_evidence'].sum())} spans"
    )
    print(f"Annotated decisive span cited as counterevidence: {ids(in_counter)}")
    print(
        f"Distinct depth_evidence spans per patient: median "
        f"{answered['n_run_depth_evidence'].median():.0f}, "
        f"range {answered['n_run_depth_evidence'].min()}-"
        f"{answered['n_run_depth_evidence'].max()}"
    )
    print(
        f"Cited any counterevidence: {int(answered['cited_counterevidence'].sum())}/{n}"
    )


def print_reading(annotated: pd.DataFrame, coverage: pd.DataFrame) -> None:
    """Print whether the model read the decisive passage and the whole document."""
    answered = annotated[annotated["run_status"] == "answered"]
    partly = answered[answered["min_frac_decisive_read"] < 1.0]
    never = answered[answered["n_decisive_unread"] > 0]
    print("\n## Read before answering (annotated patients)")
    print(f"Answered without fully reading every decisive span: {ids(partly)}")
    print(f"Answered with some decisive span entirely unread: {ids(never)}")

    print("\n## Whole-document reading (all run records)")
    for column in ["frac_read_before_first_submit", "frac_read_total"]:
        values = coverage[column].dropna()
        print(
            f"{column}: n={len(values)}, median {values.median():.2f}, "
            f"min {values.min():.2f}, read in full {int((values >= FULL_READ).sum())}"
        )
    print(
        f"Reads per record: {coverage['n_reads'].value_counts().sort_index().to_dict()}"
    )
    print(f"Records using search: {int((coverage['n_searches'] > 0).sum())}")
    print(f"Status: {coverage['status'].value_counts().to_dict()}")
    print(
        f"No-answer annotated patients: {ids(annotated[annotated['run_status'] != 'answered'])}"
    )


def write_tables(
    run: dict[str, dict],
    annotations: dict[str, dict],
    reports: dict[str, dict],
    out_dir: Path,
) -> None:
    """Build the alignment tables, save them in `out_dir`, and print a summary."""
    coverage = pd.DataFrame(
        [
            coverage_row(unit, record, reports[unit]["document"])
            for unit, record in run.items()
        ]
    )
    annotated = pd.DataFrame(
        [
            annotated_row(unit, run[unit], annotation, reports[unit]["document"])
            for unit, annotation in annotations.items()
        ]
    )
    spans = pd.DataFrame(
        [
            row
            for unit, annotation in annotations.items()
            for row in span_rows(unit, run[unit], annotation)
        ]
    )

    coverage.to_csv(out_dir / "reading_coverage_run.csv", index=False)
    annotated.to_csv(out_dir / "alignment_annotated.csv", index=False)
    spans.to_csv(out_dir / "alignment_spans.csv", index=False)
    print(f"Wrote 3 CSV files to {out_dir}")

    print_agreement(annotated)
    print_citations(annotated)
    print_reading(annotated, coverage)
