#!/usr/bin/env python
"""Build the UCEC roster, and own the cohort filter the other prep scripts share.

The delivered data is pan-cancer: TCGA_Reports.csv carries 9,523 reports across
686 tissue source sites, and aws_response_txt carries OCR pages for all of them.
This script narrows both to the endometrial (UCEC) cohort named in the case
manifest and writes:

    $DATA_DIR/endometrial/roster_ucec.csv               one column, `unit`, one barcode per row
    $DATA_DIR/endometrial/sources/ucec_pathology_pages.txt pipe-delimited, one row per OCR page

The roster is what a run iterates, and this script is its owner.

The page table beside it is NOT an oncotrace input. oncotrace reads a JSON Lines
document store and nothing else, which scripts/endometrial_data/build_ucec_document_store.py writes.
The table survives as a flat, greppable view of the same pages for inspecting the
delivery by hand, and that is why its text goes through csv.writer: a page
holding a literal '|', a quote, or newlines is quoted rather than mangled.

Two functions here are shared owners, imported rather than reimplemented by the
other prep scripts: read_cohort, which decides who is in the cohort, and
collect_pages, which holds the OCR filename contract and the numeric page sort
("..._Page_10.txt" sorts before "..._Page_1.txt" as text, which would scramble a
report). Change either here and every producer follows.

Nothing here writes into the repository: --out-dir defaults to $DATA_DIR/endometrial, which
.gitignore excludes.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(os.environ.get("DATA_DIR", "data")) / "endometrial"

# TCGA-E6-A1M0.F1AF61FE-BF05-49E2-85DA-F4CE37596DEA_Page_1.txt
#  ^barcode      ^document uuid (case varies)                ^page
PAGE_NAME = re.compile(
    r"^(?P<barcode>TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})"
    r"\.(?P<document>[0-9A-Fa-f-]+)"
    r"_Page_(?P<page>\d+)\.txt$"
)

#: How many missing barcodes to list before summarising the rest.
SHOWN_BARCODES = 8

HEADER = ["ALIAS", "DOCUMENT_ID", "PAGE", "PAGE_TEXT"]


def parse_args() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DATA / "ucec_cohort.tsv",
        help="cohort definition with a submitter_id column, "
        "written by scripts/endometrial_data/fetch_ucec_cohort.py",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        default=DATA / "aws_response_txt",
        help="directory of per-page OCR text files",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DATA,
        help="where to write roster and sources (default: $DATA_DIR/endometrial)",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=20,
        help="drop pages with less usable text than this "
        "(default 20; on the 2026-09-07 OCR delivery no "
        "UCEC page falls under it)",
    )
    return parser.parse_args()


def read_cohort(path: Path) -> set[str]:
    """Read the barcodes of the cohort we are narrowing to."""
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if "submitter_id" not in (reader.fieldnames or ()):
            raise SystemExit(f"{path} has no submitter_id column")
        return {value for row in reader if (value := row["submitter_id"].strip())}


def cohort_release(cases: Path) -> str:
    """Describe which GDC snapshot the cohort came from, for the build log.

    Read from the sidecar scripts/endometrial_data/fetch_ucec_cohort.py writes, so every producer
    that narrows the delivery says which release it narrowed against. A cohort
    file with no sidecar was not fetched by that script and cannot be
    re-derived, which is worth saying out loud rather than leaving blank.
    """
    sidecar = cases.with_suffix(".provenance.json")
    if not sidecar.is_file():
        return f"unknown -- no {sidecar.name}; re-derive with fetch_ucec_cohort.py"
    record = json.loads(sidecar.read_text(encoding="utf-8"))
    return (
        f"{record.get('gdc_data_release')} "
        f"(digest {str(record.get('barcode_sha256'))[:16]})"
    )


def collect_pages(
    ocr_dir: Path, cohort: set[str], min_chars: int
) -> tuple[dict[str, list[tuple[str, int, str]]], set[str], int, int, int]:
    """Return {barcode: [(document, page, text)]} plus a drop tally.

    Pages are read individually because a scanned report is delivered one file
    per page; the grouping back into a patient happens here rather than in the
    config, which only knows about rows.
    """
    kept: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    #: Cohort barcodes that had at least one page file, whatever became of it.
    #: Without this the roster can report that a patient is absent but not
    #: whether the delivery lacked their scan or their pages were all empty --
    #: two different problems, one to chase with whoever sent the data and one to
    #: chase with --min-chars.
    seen: set[str] = set()
    dropped_empty = 0
    unparsed = 0
    out_of_cohort = 0

    for entry in sorted(path.name for path in ocr_dir.iterdir()):
        match = PAGE_NAME.match(entry)
        if not match:
            unparsed += 1
            continue
        barcode = match.group("barcode")
        if barcode not in cohort:
            out_of_cohort += 1
            continue
        seen.add(barcode)
        text = (ocr_dir / entry).read_text(errors="replace").strip()
        if len(text) < min_chars:
            dropped_empty += 1
            continue
        kept[barcode].append((match.group("document"), int(match.group("page")), text))

    for pages in kept.values():
        pages.sort(key=lambda item: (item[0], item[1]))
    return kept, seen, dropped_empty, unparsed, out_of_cohort


def write_outputs(
    kept: dict[str, list[tuple[str, int, str]]], out_dir: Path
) -> tuple[Path, Path, int]:
    """Write the page table and the roster; return their paths and the row count."""
    sources_dir = out_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    source_path = sources_dir / "ucec_pathology_pages.txt"
    roster_path = out_dir / "roster_ucec.csv"

    rows = 0
    # newline="" so csv controls record boundaries; a page with embedded
    # newlines is emitted as one quoted field, not several broken rows.
    with source_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="|")
        writer.writerow(HEADER)
        for barcode in sorted(kept):
            for document, page, text in kept[barcode]:
                writer.writerow([barcode, document, page, text])
                rows += 1

    with roster_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["unit"])
        for barcode in sorted(kept):
            writer.writerow([barcode])

    return roster_path, source_path, rows


def main() -> int:
    """Run the script; return the process exit status."""
    args = parse_args()
    if not args.ocr_dir.is_dir():
        raise SystemExit(f"missing OCR directory: {args.ocr_dir}")

    cohort = read_cohort(args.cases)
    kept, seen, dropped_empty, unparsed, out_of_cohort = collect_pages(
        args.ocr_dir, cohort, args.min_chars
    )
    roster_path, source_path, rows = write_outputs(kept, args.out_dir)

    # A cohort barcode can fail to reach the roster two ways, and they are not
    # the same finding: the delivery never carried a scan for that patient, or
    # it did and every page came back under --min-chars. Report them apart.
    no_pages_at_all = sorted(cohort - seen)
    all_pages_empty = sorted(seen - set(kept))
    print(f"cohort release                   : {cohort_release(args.cases)}")
    print(f"cohort barcodes in manifest      : {len(cohort)}")
    print(f"cohort barcodes with usable pages: {len(kept)}")
    print(f"cohort barcodes absent, no scan  : {len(no_pages_at_all)}")
    print(f"cohort barcodes absent, all empty: {len(all_pages_empty)}")
    for label, group in (
        ("no scan delivered", no_pages_at_all),
        ("every page under the threshold", all_pages_empty),
    ):
        if group:
            shown = ", ".join(group[:SHOWN_BARCODES])
            extra = len(group) - SHOWN_BARCODES
            more = f" (+{extra} more)" if extra > 0 else ""
            print(f"  {label}: {shown}{more}")
    # A whole tissue source site going missing is a cohort-composition problem,
    # not a count: site is the two characters after TCGA- and tracks the
    # contributing institution and therefore its patient population.
    if no_pages_at_all:
        lost = Counter(barcode.split("-")[1] for barcode in no_pages_at_all)
        total = Counter(barcode.split("-")[1] for barcode in cohort)
        for site, count in sorted(lost.items(), key=lambda item: -item[1]):
            flag = "  <-- ENTIRE SITE" if count == total[site] else ""
            print(f"  site TCGA-{site}: {count} of {total[site]} missing{flag}")
    print(f"pages written                    : {rows}")
    print(f"pages dropped under {args.min_chars} chars     : {dropped_empty}")
    print(f"files skipped, other cohorts     : {out_of_cohort}")
    print(f"files skipped, unparsable name   : {unparsed}")
    print()
    print(f"roster : {roster_path}")
    print(f"source : {source_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
