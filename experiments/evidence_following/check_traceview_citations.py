"""Check that every citation in a run renders at the right words in TraceView.

Start TraceView on the run first (see docs/student-setup.md), then run, e.g.:

    python experiments/evidence_following/check_traceview_citations.py --port 8742 \
        --units TCGA-A5-A2K2 TCGA-A5-A0GQ

For each unit, the script asks the running viewer for its page, collects the
highlighted pieces for each citation group, and checks that the text of every
citation (sliced from the report by its offsets) appears in that group's
highlighted pieces. It prints only IDs, groups, and counts, never report text.
"""

import argparse
import html
import json
import re
import urllib.request
from pathlib import Path

from records import DEFAULT_RUN, REPORTS_PATH, load_reports, load_run

CITATION_GROUPS = [
    "depth_evidence",
    "specimen_evidence",
    "counterevidence",
    "quantified_depth",
]

# One highlighted piece: <span class="s ..." data-k="groups" ...>TEXT<sup>
PIECE = re.compile(
    r'<span class="s [^"]*"[^>]*data-k="([^"]*)"[^>]*>(.*?)<sup>', re.DOTALL
)


def get(url: str, token: str | None = None, body: dict | None = None) -> str:
    """Fetch a page from the local viewer, as a POST when `body` is given."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data)  # noqa: S310 (localhost only)
    if token:
        request.add_header("X-TraceView-Token", token)
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request) as response:  # noqa: S310
        return response.read().decode()


def squash(text: str) -> str:
    """Collapse whitespace so line wrapping does not affect the comparison."""
    return " ".join(text.split())


def check_unit(base: str, run_name: str, record: dict, report: dict) -> dict:
    """Return per-group counts of citations found and missing on the unit page."""
    page = get(f"{base}/unit?r={run_name}&u={record['unit']}")
    pieces = {group: [] for group in CITATION_GROUPS}
    for groups, text in PIECE.findall(page):
        for group in groups.split():
            if group in pieces:
                pieces[group].append(html.unescape(re.sub(r"<[^>]+>", "", text)))
    result = {}
    for group in CITATION_GROUPS:
        shown = squash("".join(pieces[group]))
        cites = record["answer"].get(group) or []
        found = sum(
            squash(report["text"][cite["start"] : cite["end"]]) in shown
            for cite in cites
        )
        result[group] = (found, len(cites))
    return result


def main() -> None:
    """Check the listed units and print one line per unit."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8742)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--reports", type=Path, default=REPORTS_PATH)
    parser.add_argument("--units", nargs="+", required=True)
    args = parser.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    run_name = args.run_dir.name
    token = re.search(r'const TOKEN = "([^"]+)"', get(base + "/")).group(1)
    get(base + "/api/load", token, {"run": run_name})

    records = load_run(args.run_dir)
    reports = load_reports(args.reports)
    for unit in args.units:
        record = records[unit]
        if record["answer"].get("status") != "answered":
            print(f"{unit}: {record['answer'].get('status')}, no citations to check")
            continue
        result = check_unit(base, run_name, record, reports[unit])
        ok = all(found == total for found, total in result.values())
        counts = ", ".join(f"{g} {f}/{t}" for g, (f, t) in result.items())
        print(f"{unit}: {'OK' if ok else 'MISSING'} ({counts})")


if __name__ == "__main__":
    main()
