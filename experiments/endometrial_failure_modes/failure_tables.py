"""The tables this experiment reports, built from TraceView's view of a run.

Each function takes what TraceView has already loaded (see
`oncotrace_bench.traceview_summary.load_views`) and returns a small table of
counts. No report text is read or written.
"""

from collections import Counter

import pandas as pd

from oncotrace_bench.traceview_summary import (
    ACCEPTED,
    OUTCOMES,
    UNFINISHED,
    outcome_of,
    refusal_counts,
)

DEPTH_FIELD = "myometrial_invasion_percent"
CONFIDENCE_COLUMNS = ("correct", "wrong", "over_committed", "abstained")


def count_frame(counts: Counter, order: tuple[str, ...], total: int) -> pd.DataFrame:
    """Turn counts into a table, listing zero counts and any unexpected value."""
    extra = sorted(set(counts) - set(order))
    rows = [(value, counts.get(value, 0)) for value in (*order, *extra)]
    frame = pd.DataFrame(rows, columns=["value", "patients"])
    frame.loc[len(frame)] = ["total", total]
    return frame


def outcome_tables(
    views: list, task: object, roster: list[str]
) -> dict[str, pd.DataFrame]:
    """Count what happened to every roster patient, and what accepted answers said.

    Every roster patient lands in exactly one outcome row, so `outcome` sums to
    the roster size; patients with no record are unfinished. An indeterminate
    clinical answer (for example `cannot_be_determined`) is an accepted answer,
    so it is counted in `invasion` and `depth`, not under no accepted submission.
    """
    by_unit = {view.unit: view for view in views}
    outcomes = {
        unit: outcome_of(by_unit[unit]) if unit in by_unit else UNFINISHED
        for unit in roster
    }
    accepted = [by_unit[unit] for unit, kind in outcomes.items() if kind == ACCEPTED]
    invasion = Counter(view.label for view in accepted)
    depth = Counter(view.fields.get(DEPTH_FIELD) or "(blank)" for view in accepted)
    return {
        "outcome": count_frame(Counter(outcomes.values()), OUTCOMES, len(roster)),
        "invasion": count_frame(invasion, task.label_values, len(accepted)),
        "depth": count_frame(
            depth, task.extra_field(DEPTH_FIELD).values, len(accepted)
        ),
    }


def confidence_table(views: list, task: object, reference: object) -> pd.DataFrame:
    """Agreement with the human annotations, grouped by the model's confidence.

    Patients are matched to annotations by ID. Each patient is `correct` (label
    matches), `wrong` (differs), `over_committed` (asserts a value where the
    human said not applicable or cannot be determined), or `abstained` (no
    accepted answer, which has no confidence and sits in the `none` row).
    The agreement rules are TraceView's own (`scoring.agreement_state`).
    """
    import scoring

    predicted, _ = scoring.predictions(views)
    # The reference is (labels by unit, annotation status by unit, blank count).
    labels, _, _ = reference
    confidence = {view.unit: view.confidence for view in views}
    matched = sorted(set(predicted) & set(labels))

    counts: dict[str, Counter] = {}
    for unit in matched:
        state = scoring.agreement_state(predicted[unit], labels[unit])
        group = confidence[unit] if predicted[unit] is not None else "none"
        counts.setdefault(group or "none", Counter())[state] += 1

    known = [
        *task.confidence_values,
        *sorted(set(counts) - {*task.confidence_values, "none"}),
        "none",
    ]
    rows = [
        {
            "confidence": group,
            "patients": sum(counts.get(group, Counter()).values()),
            **{col: counts.get(group, Counter())[col] for col in CONFIDENCE_COLUMNS},
        }
        for group in known
    ]
    frame = pd.DataFrame(rows)
    frame.loc[len(frame)] = ["total", *frame.drop(columns="confidence").sum()]
    return frame


def refusal_summary(views: list) -> pd.DataFrame:
    """Group refusals by signature: patients affected and refusals recorded.

    Splits the patients into those that went on to an accepted answer and those
    that did not, so a refusal that is routinely recovered from can be told
    apart from one that ends a run.
    """
    rows: dict[str, dict[str, int]] = {}
    for view in views:
        for signature, count in refusal_counts(view).items():
            row = rows.setdefault(
                signature,
                {"patients": 0, "refusals": 0, "answered": 0, "no_answer": 0},
            )
            row["patients"] += 1
            row["refusals"] += count
            row["answered" if view.answered else "no_answer"] += 1
    frame = pd.DataFrame.from_dict(rows, orient="index")
    return (
        frame.sort_values("patients", ascending=False)
        .rename_axis("signature")
        .reset_index()
    )
