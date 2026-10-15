"""Count what happened to every roster patient in an OncoTrace run.

All reading of run records is done by TraceView (`viewer/records.py` in the
OncoTrace clone) and OncoTrace's `is_server_error`. This module only sorts
TraceView's results into the outcome table; it does not parse records itself.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ACCEPTED = "accepted answer"
NO_ANSWER = "no accepted submission"
SERVER_ERROR = "server error"
UNFINISHED = "unfinished (no record)"
OUTCOMES = (ACCEPTED, NO_ANSWER, SERVER_ERROR, UNFINISHED)

DEPTH_FIELD = "myometrial_invasion_percent"


def add_traceview_to_path(oncotrace_dir: Path) -> None:
    """Make TraceView's modules (`records`) and `oncotrace` importable."""
    for folder in (oncotrace_dir / "viewer", oncotrace_dir):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))


def read_roster(roster_csv: Path, column: str = "unit") -> list[str]:
    """Return the patient IDs in the roster, in file order."""
    with roster_csv.open(encoding="utf-8", newline="") as handle:
        return [row[column] for row in csv.DictReader(handle)]


def outcome_of(view: object) -> str:
    """Classify one TraceView record as accepted, no answer, or server error."""
    from oncotrace.score import is_server_error

    if is_server_error(view.record.get("answer")):
        return SERVER_ERROR
    if view.answered:
        return ACCEPTED
    if view.status == "no_answer":
        return NO_ANSWER
    # A record in some other state is not a finished patient.
    return UNFINISHED


def outcome_table(
    run_dir: Path, task_yaml: Path, roster: list[str]
) -> dict[str, pd.DataFrame]:
    """Build the outcome, invasion, and depth tables for one run.

    Every roster patient lands in exactly one outcome row, so the outcome
    table sums to the roster size. Patients with no record are unfinished.
    """
    import records as traceview

    tasks, _, _ = traceview.load_tasks([task_yaml])
    task = next(iter(tasks.values()))
    views = {view.unit: view for view in traceview.load_run(run_dir, tasks)}

    outcomes = {unit: outcome_of(views[unit]) if unit in views else UNFINISHED
                for unit in roster}
    outcome_counts = Counter(outcomes.values())

    accepted = [views[unit] for unit, kind in outcomes.items() if kind == ACCEPTED]
    invasion = Counter(view.label for view in accepted)
    depth = Counter(view.fields.get(DEPTH_FIELD) or "(blank)" for view in accepted)

    return {
        "outcome": _count_frame(outcome_counts, OUTCOMES, len(roster)),
        "invasion": _count_frame(invasion, task.label_values, len(accepted)),
        "depth": _count_frame(
            depth, task.extra_field(DEPTH_FIELD).values, len(accepted)
        ),
    }


def _count_frame(counts: Counter, order: tuple[str, ...], total: int) -> pd.DataFrame:
    """Turn counts into a table, listing zero counts and any unexpected value."""
    extra = sorted(set(counts) - set(order))
    rows = [(value, counts.get(value, 0)) for value in (*order, *extra)]
    frame = pd.DataFrame(rows, columns=["value", "patients"])
    frame.loc[len(frame)] = ["total", total]
    return frame


def trajectory_facts(view: object) -> dict:
    """Summarize one patient's recorded steps without any report text.

    Uses TraceView's already-loaded record. Only counts, tool names, refusal
    signatures, and character offsets are returned, so the result is safe to
    paste into notes (report text, quotes, and rationales are protected).
    """
    events = view.record.get("events") or []
    refusals = [e for e in events if e.get("kind") == "recoverable_error"]
    quote_lengths = [
        (e.get("diagnostics") or {}).get("quote_chars")
        for e in refusals
        if e.get("signature") == "citation_quote_not_found"
    ]
    windows = [
        (w["start"], w["end"]) for found in view.windows.values() for w in found
    ]
    return {
        "unit": view.unit,
        "outcome": view.reason if not view.answered else "answered",
        "label": view.label,
        "confidence": view.confidence,
        "steps": view.shape,
        "model_calls": view.model_calls,
        "document_chars": view.document_chars,
        "read_windows": windows,
        "chars_read": view.chars_read,
        "refusals": Counter(e.get("signature") for e in refusals),
        "single_char_quotes": sum(length == 1 for length in quote_lengths),
        "not_found_quotes": len(quote_lengths),
        "truncated_replies": view.truncated,
        "max_completion_tokens": view.max_completion,
        "last_event": events[-1].get("kind") if events else None,
    }
