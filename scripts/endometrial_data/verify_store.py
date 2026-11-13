#!/usr/bin/env python
"""Check that a locally built report store is the one the clinic's runs used.

Three checks, in order of strictness:

1. The roster lists 546 patients and the store holds one report for each.
2. Every quote saved in ``annotations/`` appears in the store at exactly its
   saved character range. Annotations cite reports by character position, so
   if this fails the annotations do not line up with your reports.
3. The store's SHA-256 matches the shared copy recorded in
   ``docs/endometrial-data.md``. A match means your file is byte-for-byte
   identical to the one every earlier run read.

Prints a line per check and exits nonzero if any fails.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

DATA = Path(os.environ.get("DATA_DIR", "data")) / "endometrial"
REPO = Path(__file__).resolve().parents[2]

EXPECTED_PATIENTS = 546
EXPECTED_SHA256 = "d0f547d43adc8076e11a821244734c8adb3f4fc0570c0d6d884821b0a220087f"


def parse_args() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--store", type=Path, default=DATA / "documents" / "ucec_pathology_report.jsonl"
    )
    parser.add_argument("--roster", type=Path, default=DATA / "roster_ucec.csv")
    parser.add_argument("--annotations", type=Path, default=REPO / "annotations")
    return parser.parse_args()


def main() -> int:
    """Run the script; return the process exit status."""
    args = parse_args()
    ok = True

    with args.roster.open(newline="") as handle:
        roster = [row["unit"] for row in csv.DictReader(handle)]
    documents = {}
    with args.store.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            documents[(record["unit"], record["document"])] = record["text"]
    units = {unit for unit, _ in documents}
    counts_ok = len(roster) == EXPECTED_PATIENTS and units == set(roster)
    print(
        f"[{'ok' if counts_ok else 'FAIL'}] patients: roster {len(roster)}, store {len(units)}, "
        f"expected {EXPECTED_PATIENTS}"
    )
    ok &= counts_ok

    checked = mismatched = 0
    for path in sorted(args.annotations.glob("*/*.json")):
        annotation = json.loads(path.read_text(encoding="utf-8"))
        for field in annotation.get("fields", {}).values():
            for span in field.get("spans", []):
                checked += 1
                text = documents.get((annotation["unit"], span["document"]))
                if text is None or text[span["start"] : span["end"]] != span["text"]:
                    mismatched += 1
    quotes_ok = checked > 0 and mismatched == 0
    print(
        f"[{'ok' if quotes_ok else 'FAIL'}] annotation quotes at their saved positions: "
        f"{checked - mismatched} of {checked}"
    )
    ok &= quotes_ok

    digest = hashlib.sha256(args.store.read_bytes()).hexdigest()
    sha_ok = digest == EXPECTED_SHA256
    print(
        f"[{'ok' if sha_ok else 'FAIL'}] store SHA-256 {'matches' if sha_ok else 'differs from'} "
        f"the shared copy"
    )
    ok &= sha_ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
