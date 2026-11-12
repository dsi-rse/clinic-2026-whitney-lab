#!/usr/bin/env python
"""Turn the public TCGA-Reports OCR archive into one text file per report page.

The TCGA pathology reports are scanned PDFs. Kefeli & Tatonetti (Patterns 2024,
doi:10.1016/j.patter.2024.100933) ran every page through Amazon Textract and
published the raw responses as ``aws_response.tar.gz``. Each member is one page:

    aws_response/TCGA-E6-A1M0.F1AF61FE-..._Page_1_response.p

This script reads that archive without unpacking it, keeps only the patients in
the cohort file, and writes each page's text to

    <out-dir>/TCGA-E6-A1M0.F1AF61FE-..._Page_1.txt

which is the input ``build_ucec_sources.py`` and ``build_ucec_document_store.py``
expect. A page's text is its Textract LINE blocks, in the order Textract returned
them, one per line.

Each response is a Python pickle. Loading a pickle can run code, so the loader
here refuses every class reference: a Textract response is plain dicts, lists,
strings and numbers, and anything else stops the script.
"""

from __future__ import annotations

import argparse
import csv
import os
import pickle
import re
import sys
import tarfile
from pathlib import Path
from typing import NoReturn

DATA = Path(os.environ.get("DATA_DIR", "data")) / "endometrial"

MEMBER = re.compile(
    r"^aws_response/(?P<page>(?P<barcode>TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})\.[0-9A-Fa-f-]+_Page_\d+)_response\.p$"
)


class DataOnlyUnpickler(pickle.Unpickler):
    """Load plain data only; refuse any class or function reference."""

    def find_class(self, module: str, name: str) -> NoReturn:
        """Refuse every class reference."""
        raise pickle.UnpicklingError(f"refusing to load {module}.{name}")


def parse_args() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=DATA / "downloads" / "aws_response.tar.gz",
        help="the downloaded aws_response.tar.gz",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DATA / "ucec_cohort.tsv",
        help="cohort file from fetch_ucec_cohort.py (submitter_id column)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DATA / "aws_response_txt",
        help="where to write one .txt per page",
    )
    return parser.parse_args()


def read_cohort(path: Path) -> set[str]:
    """Read the cohort barcodes from the submitter_id column."""
    with path.open(newline="") as handle:
        return {
            row["submitter_id"].strip()
            for row in csv.DictReader(handle, delimiter="\t")
        }


def page_text(response: dict) -> str:
    """Join a Textract page's LINE blocks into text, one line each."""
    return "\n".join(
        block["Text"] for block in response["Blocks"] if block["BlockType"] == "LINE"
    )


def main() -> int:
    """Run the script; return the process exit status."""
    args = parse_args()
    cohort = read_cohort(args.cases)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    patients = set()
    with tarfile.open(args.archive, "r|gz") as archive:
        for member in archive:
            match = MEMBER.match(member.name)
            if not member.isfile() or not match or match.group("barcode") not in cohort:
                continue
            response = DataOnlyUnpickler(archive.extractfile(member)).load()
            (args.out_dir / f"{match.group('page')}.txt").write_text(
                page_text(response), encoding="utf-8"
            )
            written += 1
            patients.add(match.group("barcode"))
    print(f"cohort patients          : {len(cohort)}")
    print(f"patients with OCR pages  : {len(patients)}")
    print(f"pages written            : {written}")
    print(f"pages directory          : {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
