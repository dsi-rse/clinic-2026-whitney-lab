#!/usr/bin/env python
r"""Build the UCEC document store: the JSON Lines input oncotrace reads.

What this writes
----------------
    $DATA_DIR/endometrial/documents/ucec_pathology_report.jsonl

One JSON object per line, one line per *document* -- a document being one whole
pathology report, every OCR page of it stitched in page order:

    {"document": "<uuid>", "metadata": {"page_count": "4"},
     "text": "===== PAGE 1 =====\\n...", "unit": "<barcode>"}

`unit`, `document` and `text` are required; only `date` and `metadata` are
permitted besides. oncotrace/records.py is the sole reader of the format and
refuses an unknown key rather than ignoring it, because the common mistake is a
misspelled one -- a "txt" key would otherwise read as a document with no text.
oncotrace's README.md specifies the format normatively.

Why this conversion lives here and not in oncotrace
---------------------------------------------------
Turning a delivery into a store is a set of judgements about *this* delivery:
which files belong to one report, in what order, what counts as a page, what to
do with a byte that is not valid UTF-8. None of that is a fact about extraction,
so oncotrace requires the format instead of inferring it, and the conversion is
the producer's. Freezing those judgements in one script, ahead of any run, is
what makes a citation durable: the report is reconstituted once, before anything
cites it, rather than depending on how a given run happened to group rows.

Why a citation is a character range, and what that costs
--------------------------------------------------------
A citation is `(source, document, start, end)`: a half-open range of code
points into `text`, exactly as Python indexes a `str`. So `text` has to be the
exact surface the model was shown, and any character added or removed moves
every offset after it. Three consequences, none of them optional:

  * All normalisation happens HERE, before the store exists. Newlines are folded
    to a bare \\n and NUL bytes dropped while the text is still the producer's
    to change. oncotrace refuses both rather than stripping them, because
    stripping would move offsets under whoever already cited the text.
  * Nothing is normalised afterwards -- no NFC/NFKC, no re-wrapping, no
    whitespace tidying. Unicode normalisation alone can change the code point
    count.
  * Rebuilding this store with different arguments invalidates a completed run's
    citations. They still resolve; they quietly point at different words. That is
    what oncotrace's `projection_fingerprint` exists to catch.

One document per report, not per page
-------------------------------------
Pages are stitched because a finding split across two documents cannot be cited
as one quote, which is the most common way to make a task contract
unsatisfiable. Page identity survives as `===== PAGE n =====` markers inside the
text: prose the model can quote, not a checked reference. There is deliberately
no flag to suppress the markers -- two stores of the same name whose offsets
differ is exactly the hazard the fingerprint has to warn about, so the marker
decision is fixed in code rather than left to a command line.

A patient holding two separate reports gets two lines, one per document. `unit`
repeats freely across lines; `document` is what must be unique within the store.
That is why this script has no equivalent of the one-document-per-patient refusal
its predecessor needed: a single row per patient could only have held two reports
interleaved in one field, with no way to tell which sentence came from which.

Encoding is the producer's problem
----------------------------------
A store is UTF-8, and oncotrace will not guess an encoding or substitute
replacement characters, because a substitution changes the character count. So
pages are decoded strictly and a page that is not valid UTF-8 stops the build
before anything is written. `--allow-lossy-decode` accepts U+FFFD substitution
instead; either way the tally is printed, so the decision is recorded rather
than absorbed.

No identifier is ever printed. Every count below is an aggregate, because a TCGA
barcode is patient-derived and this script's output lands in job logs
(CLAUDE.md section 7).

Regenerate with:
    micromamba run -p ~/oncotrace-dsi/envs/oncotrace-client \
      python scripts/endometrial_data/build_ucec_document_store.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

# The cohort filter and the OCR filename contract have one owner, the page-level
# builder, so a change to either happens in one place. The decode policy and the
# grouping are this producer's own judgement and live here, which is precisely
# the split the input format asks for.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_ucec_sources import (  # noqa: E402
    DATA,
    PAGE_NAME,
    cohort_release,
    read_cohort,
)

# oncotrace's own reader validates what this writes, so the producer proves its
# output is readable instead of asserting it. Resolved the way the existing
# check scripts resolve it: ONCOTRACE_REPO if set, else the working copy.
sys.path.insert(
    0, os.environ.get("ONCOTRACE_REPO", str(Path("~/oncotrace").expanduser()))
)
from oncotrace.records import SourceSpec, units  # noqa: E402

#: The name citations refer to this store by. A task config declares the same
#: name, and it is part of the provenance of every label, so it should not be
#: renamed under a completed run.
SOURCE_NAME = "pathology_report"

STORE_NAME = "ucec_pathology_report.jsonl"

#: Greppable, and distinct from the scanner's own "Page 1 of 4" furniture that
#: already appears inside the OCR text.
PAGE_MARKER = "===== PAGE {page} ====="


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
        help="where to write the store (default: $DATA_DIR/endometrial)",
    )
    parser.add_argument(
        "--roster",
        type=Path,
        default=DATA / "roster_ucec.csv",
        help="roster to cross-check units against; the store and "
        "the roster must agree exactly",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=20,
        help="drop pages with less usable text than this "
        "(default 20, matching build_ucec_sources.py)",
    )
    parser.add_argument(
        "--allow-lossy-decode",
        action="store_true",
        help="accept U+FFFD substitution for pages that are not "
        "valid UTF-8 instead of refusing to build",
    )
    return parser.parse_args()


def scrub(text: str, tally: Counter) -> str:
    r"""Make one page's text storable: bare \\n newlines, no NUL bytes.

    This is the only place the text is altered, and it happens before the store
    exists, so no citation can yet depend on the offsets it moves. Everything
    else is left exactly as delivered.
    """
    if "\r" in text:
        tally["pages_with_carriage_return"] += 1
        # \r\n first, so a Windows line ending collapses to one newline rather
        # than two; a lone \r then becomes the newline it was standing in for.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\x00" in text:
        tally["pages_with_nul"] += 1
        text = text.replace("\x00", "")
    return text


def collect_documents(
    ocr_dir: Path, cohort: set[str], min_chars: int, allow_lossy: bool
) -> tuple[dict[tuple[str, str], list[tuple[int, str]]], Counter]:
    """Return {(unit, document): [(page number, page text)]} and a tally.

    Grouping is by (patient, document) because the store keys a document rather
    than a row: a patient with two reports yields two lines that stay separately
    citable.
    """
    grouped: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    tally: Counter = Counter()

    for entry in sorted(path.name for path in ocr_dir.iterdir()):
        match = PAGE_NAME.match(entry)
        if not match:
            tally["skipped_unparsable_name"] += 1
            continue
        barcode = match.group("barcode")
        if barcode not in cohort:
            tally["skipped_other_cohort"] += 1
            continue

        raw = (ocr_dir / entry).read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            tally["pages_not_utf8"] += 1
            if not allow_lossy:
                # Keep scanning so the operator gets the full count rather than
                # the first offender; main() refuses before anything is written.
                continue
            text = raw.decode("utf-8", errors="replace")
            tally["replacement_characters"] += text.count("�")

        text = scrub(text, tally).strip()
        if len(text) < min_chars:
            tally["dropped_short_page"] += 1
            continue

        grouped[(barcode, match.group("document"))].append(
            (int(match.group("page")), text)
        )
        tally["pages_kept"] += 1

    for pages in grouped.values():
        # By page number, not by filename: "..._Page_10.txt" sorts BEFORE
        # "..._Page_1.txt" as text, which would silently scramble a report.
        pages.sort()
    return grouped, tally


def render_report(pages: list[tuple[int, str]]) -> str:
    r"""Stitch one document's pages into one text, in page order.

    `pages` arrives already sorted, so this does not re-sort: re-sorting here
    would hide a change to the sort upstream. The "\\n\\n".join is what
    guarantees two pages' words can never touch -- no page file ends in a
    newline, so a bare concatenation would weld the last word of one page onto
    the first word of the next.
    """
    return "\n\n".join(
        f"{PAGE_MARKER.format(page=page_no)}\n{text}" for page_no, text in pages
    )


def write_store(
    grouped: dict[tuple[str, str], list[tuple[int, str]]], out_dir: Path
) -> tuple[Path, list[int]]:
    """Write one JSON object per document and return the path and text lengths."""
    documents_dir = out_dir / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    path = documents_dir / STORE_NAME

    lengths: list[int] = []
    # newline="\n" so the record separator is the one the format specifies
    # whatever platform this runs on. ensure_ascii=True keeps the file plain
    # ASCII bytes: a \uXXXX escape is still one code point to json.loads, so
    # escaping cannot move a citation's offsets.
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for (unit, document), pages in sorted(grouped.items()):
            text = render_report(pages)
            entry = {
                "unit": unit,
                "document": document,
                # A flat string map: values are strings even when they count
                # something, which is what lets the inventory render any store
                # without knowing anything about it. The document's length is
                # not here because the inventory already reports
                # document_chars from the text itself.
                "metadata": {"page_count": str(len(pages))},
                "text": text,
            }
            # `date` is omitted rather than written empty. TCGA scans are
            # undated and the case manifest carries no collection date, and an
            # empty string would claim we had a date and lost it.
            handle.write(json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n")
            lengths.append(len(text))
    return path, lengths


def read_roster(path: Path) -> set[str]:
    """Read the units a run will be asked for, so the store can be compared to it."""
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if "unit" not in (reader.fieldnames or ()):
            raise SystemExit(f"{path} has no unit column")
        return {row["unit"].strip() for row in reader if row["unit"].strip()}


def main() -> int:
    """Run the script; return the process exit status."""
    args = parse_args()
    if not args.ocr_dir.is_dir():
        raise SystemExit(f"missing OCR directory: {args.ocr_dir}")

    cohort = read_cohort(args.cases)
    grouped, tally = collect_documents(
        args.ocr_dir, cohort, args.min_chars, args.allow_lossy_decode
    )

    # Refuse before writing: a store built from a partial decode is worse than
    # no store, because nothing downstream can see which pages went missing.
    if tally["pages_not_utf8"] and not args.allow_lossy_decode:
        print(f"pages that are not valid UTF-8   : {tally['pages_not_utf8']}")
        print("a store is UTF-8 and its producer owns every encoding decision.")
        print("re-run with --allow-lossy-decode to accept U+FFFD substitution,")
        print("or fix the delivery. nothing was written.")
        return 1

    path, lengths = write_store(grouped, args.out_dir)

    # Read it back through oncotrace's enforcing reader. This parses every line
    # and rejects anything the format forbids -- an unknown key, a padded
    # identifier, a repeated document, a carriage return -- naming the file and
    # line. It is the check that stands in for a test file.
    found = set(units((SourceSpec(name=SOURCE_NAME, path=path),)))

    documents_per_unit = Counter(unit for unit, _document in grouped)
    multi = sum(1 for count in documents_per_unit.values() if count > 1)
    lengths.sort()
    median = lengths[len(lengths) // 2] if lengths else 0

    print(f"cohort release                   : {cohort_release(args.cases)}")
    print(f"cohort barcodes in manifest      : {len(cohort)}")
    print(f"units written                    : {len(documents_per_unit)}")
    print(f"units with more than one document: {multi}")
    print(f"documents written                : {len(lengths)}")
    print(f"pages kept                       : {tally['pages_kept']}")
    print(
        f"pages dropped under {args.min_chars} chars     : "
        f"{tally['dropped_short_page']}"
    )
    print(f"files skipped, other cohorts     : {tally['skipped_other_cohort']}")
    print(f"files skipped, unparsable name   : {tally['skipped_unparsable_name']}")
    print()
    print(f"pages with a carriage return     : {tally['pages_with_carriage_return']}")
    print(f"pages with a NUL byte            : {tally['pages_with_nul']}")
    print(f"pages that are not valid UTF-8   : {tally['pages_not_utf8']}")
    print(f"U+FFFD substitutions made        : {tally['replacement_characters']}")
    print()
    print(
        f"document length min/median/max   : "
        f"{lengths[0] if lengths else 0} / {median} / "
        f"{lengths[-1] if lengths else 0}"
    )
    print(f"units read back by oncotrace     : {len(found)}")

    # The roster is what a run iterates; a unit in one and not the other is
    # silently skipped work, so disagreement is an error and not a warning.
    if args.roster.is_file():
        rostered = read_roster(args.roster)
        print(f"units in roster                  : {len(rostered)}")
        missing = len(rostered - found)
        extra = len(found - rostered)
        print(f"rostered units absent from store : {missing}")
        print(f"stored units absent from roster  : {extra}")
        if missing or extra:
            print(
                "the store and the roster disagree; rebuild both from the same "
                "--min-chars, or reconcile before running."
            )
            return 1
    else:
        print(f"units in roster                  : not checked, no {args.roster}")

    print()
    print(f"store  : {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
