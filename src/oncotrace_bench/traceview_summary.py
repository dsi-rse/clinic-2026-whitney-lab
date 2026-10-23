"""General helpers for reading an OncoTrace run through TraceView.

TraceView (`viewer/records.py` in the OncoTrace clone) does all the reading of
run records. These helpers only make it importable from here and add a few
small summaries that any task's analysis can reuse. Nothing here is specific
to one task or dataset.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

ACCEPTED = "accepted answer"
NO_ANSWER = "no accepted submission"
SERVER_ERROR = "server error"
UNFINISHED = "unfinished (no record)"
OUTCOMES = (ACCEPTED, NO_ANSWER, SERVER_ERROR, UNFINISHED)


def add_traceview_to_path(oncotrace_dir: Path) -> None:
    """Make TraceView's modules (`records`, `annotate`, `scoring`) and `oncotrace` importable."""
    for folder in (oncotrace_dir / "viewer", oncotrace_dir):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))


def load_views(run_dir: Path, task_yaml: Path) -> tuple[list, object]:
    """Load every record in a run through TraceView, in unit order.

    Returns the list of patient views and the task contract they were read with.
    """
    import records as traceview

    tasks, _, _ = traceview.load_tasks([task_yaml])
    task = next(iter(tasks.values()))
    return traceview.load_run(run_dir, tasks), task


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


def refusal_counts(view: object) -> Counter:
    """Count how often each refusal signature was recorded for one patient."""
    events = view.record.get("events") or []
    return Counter(
        e.get("signature") for e in events if e.get("kind") == "recoverable_error"
    )


def trajectory_facts(view: object) -> dict:
    """Summarize one patient's recorded steps without any report text.

    Only counts, tool names, refusal signatures, and character offsets are
    returned, so the result is safe to paste into notes (report text, quotes,
    and rationales are protected).
    """
    events = view.record.get("events") or []
    refusals = refusal_counts(view)
    quote_lengths = [
        (e.get("diagnostics") or {}).get("quote_chars")
        for e in events
        if e.get("kind") == "recoverable_error"
        and e.get("signature") == "citation_quote_not_found"
    ]
    windows = [(w["start"], w["end"]) for found in view.windows.values() for w in found]
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
        "refusals": dict(refusals),
        "single_char_quotes": sum(length == 1 for length in quote_lengths),
        "not_found_quotes": len(quote_lengths),
        "truncated_replies": view.truncated,
        "max_completion_tokens": view.max_completion,
        "last_event": events[-1].get("kind") if events else None,
    }
