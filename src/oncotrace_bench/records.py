"""Load OncoTrace run records, annotations, and reports for analysis.

Reports, run records, and annotations all hold protected text. Functions here
return that text so it can be sliced by offset, but scripts that use them
should write only patient IDs, offsets, and labels to anything shared.
"""

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

# Read-only inputs for the endometrial study.
REPORTS_PATH = Path(
    "/net/spaces/annawoodard/oncotrace/data/endometrial/documents/"
    "ucec_pathology_report.jsonl"
)
ANNOTATIONS_DIR = REPO_ROOT / "annotations" / "endo_myometrial_invasion"

# Student workspace for run outputs and text-bearing analysis outputs. Set
# ONCOTRACE_WORKSPACE to use your own; the default is where the issue 8 runs live.
WORKSPACE = Path(
    os.environ.get(
        "ONCOTRACE_WORKSPACE", "/net/spaces/annawoodard/oncotrace/workspaces/khyatt"
    )
)
DEFAULT_RUN = WORKSPACE / "runs" / "2026-10-09_endometrial_glm53"
ANALYSIS_DIR = WORKSPACE / "analysis" / "issue8"


def load_reports(path: Path = REPORTS_PATH) -> dict[str, dict]:
    """Return {unit: {"document": ..., "text": ...}} from a report store file."""
    reports = {}
    with path.open() as f:
        for line in f:
            row = json.loads(line)
            reports[row["unit"]] = {"document": row["document"], "text": row["text"]}
    return reports


def load_annotations(directory: Path = ANNOTATIONS_DIR) -> dict[str, dict]:
    """Return {unit: annotation} for every annotation file in a directory."""
    return {
        path.stem: json.loads(path.read_text())
        for path in sorted(directory.glob("*.json"))
    }


def load_run(run_dir: Path = DEFAULT_RUN) -> dict[str, dict]:
    """Return {unit: record} for every finished unit record in a run folder."""
    return {
        path.stem: json.loads(path.read_text())
        for path in sorted((run_dir / "units").glob("*.json"))
    }


def overlap(a: dict, b: dict) -> int:
    """Return how many characters two spans share (0 if different documents)."""
    if a["document"] != b["document"]:
        return 0
    return max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))


def best_overlap(span: dict, others: list[dict]) -> float:
    """Return the largest fraction of `span` covered by any one span in `others`."""
    length = span["end"] - span["start"]
    if length <= 0 or not others:
        return 0.0
    return max(overlap(span, other) for other in others) / length


def read_windows(record: dict, before_sequence: int | None = None) -> list[dict]:
    """Return the windows the model was shown by `read` calls, as spans.

    If `before_sequence` is given, only reads that happened before that event
    sequence number are included.
    """
    windows = []
    for event in record["events"]:
        if event["kind"] != "read":
            continue
        if before_sequence is not None and event["sequence"] >= before_sequence:
            continue
        for window in event["result"].get("windows", []):
            windows.append(
                {
                    "document": window["document"],
                    "start": window["start"],
                    "end": window["end"],
                }
            )
    return windows


def covered_fraction(span: dict, windows: list[dict]) -> float:
    """Return the fraction of `span` covered by the union of `windows`."""
    length = span["end"] - span["start"]
    if length <= 0:
        return 0.0
    covered = set()
    for window in windows:
        if window["document"] == span["document"]:
            start = max(span["start"], window["start"])
            end = min(span["end"], window["end"])
            covered.update(range(start, end))
    return len(covered) / length
