#!/usr/bin/env python
"""Fetch the cohort definition from the GDC API, with its provenance beside it.

What this writes
----------------
    $DATA_DIR/endometrial/ucec_cohort.tsv                   case_id, submitter_id -- one case per row
    $DATA_DIR/endometrial/ucec_cohort.provenance.json       the query, the release, and a digest

This is the FIRST step of the pipeline and the only one that reaches the network.
Everything downstream -- the roster, the document store, the sample drawn for the
hand read -- narrows the pan-cancer delivery to the barcodes listed here, so this
file is the cohort's definition and nothing else in the repository is.

Why this exists
---------------
The cohort was previously a TSV exported by hand from the GDC Data Portal web
interface. It was correct, but it was not reproducible: the query that produced it
lived in a browser session, so nobody downstream could say which filter was
applied, against which data release, or whether a rebuild would draw the same
patients. A cohort you cannot re-derive is a cohort you cannot defend on a slide.

The query is one filter -- `cases.project.project_id in [TCGA-UCEC]` -- and it is
written into the provenance sidecar verbatim, next to the GDC data release the
answer came from, so a reader can reissue it.

Cohort drift is made loud, not absorbed
---------------------------------------
The GDC is a live archive: cases are added and occasionally redacted between data
releases. So the sidecar records a sha256 over the sorted barcode list, and a
later fetch that disagrees with it **refuses to overwrite** unless
--allow-cohort-change is passed, printing how many barcodes were added and
removed. A silently changed cohort would invalidate every label built against the
old one while every file still looked fine.

Reproducible does not mean frozen. Re-running this after a new GDC release may
legitimately return a different cohort; the point is that the change announces
itself and gets a new digest, rather than being discovered later as an
unexplained count.

Pagination is checked rather than assumed
-----------------------------------------
The API pages its results. This asks for more than the cohort can plausibly hold
and then requires the number of returned hits to equal the `total` the API
reports; a short page is an error, because a cohort that is quietly truncated is
indistinguishable from one that shrank.

Run it:
    micromamba run -p ~/oncotrace-dsi/envs/oncotrace-client \
      python scripts/endometrial_data/fetch_ucec_cohort.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

DATA = Path(os.environ.get("DATA_DIR", "data")) / "endometrial"

CASES_ENDPOINT = "https://api.gdc.cancer.gov/cases"
STATUS_ENDPOINT = "https://api.gdc.cancer.gov/status"

#: Columns of the written TSV. `submitter_id` is the TCGA barcode every other
#: prep script filters on; `case_id` is the GDC UUID that resolves to the case in
#: the portal, and is kept so a row can be looked up without a second query.
HEADER = ["case_id", "submitter_id"]

TIMEOUT_SECONDS = 60


def parse_args() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--project-id",
        default="TCGA-UCEC",
        help="GDC project to fetch (default TCGA-UCEC)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DATA / "ucec_cohort.tsv",
        help="where to write the cohort TSV; the provenance "
        "sidecar is written beside it",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=5000,
        help="cases requested in one call; must exceed the "
        "cohort, and the returned count is checked against "
        "the total the API reports (default 5000)",
    )
    parser.add_argument(
        "--allow-cohort-change",
        action="store_true",
        help="permit overwriting when the barcode digest differs "
        "from the existing sidecar's",
    )
    return parser.parse_args()


def get_json(url: str, params: dict[str, str] | None = None) -> dict:
    """Fetch one JSON document, or fail with the status and body.

    A failed cohort fetch must stop the pipeline rather than leave the previous
    file in place looking current, so nothing here is caught and retried.
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 (fixed https GDC endpoints)
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"GDC returned HTTP {error.code} for {url}\n{body}") from None
    except urllib.error.URLError as error:
        raise SystemExit(
            f"cannot reach the GDC API ({error.reason}). This step needs the "
            "network; it is the only one that does."
        ) from None


def fetch_cases(project_id: str, page_size: int) -> list[dict[str, str]]:
    """Return every case in one GDC project, as {case_id, submitter_id}."""
    filters = {
        "op": "in",
        "content": {"field": "cases.project.project_id", "value": [project_id]},
    }
    payload = get_json(
        CASES_ENDPOINT,
        {
            "filters": json.dumps(filters, separators=(",", ":")),
            "fields": ",".join(HEADER),
            "size": str(page_size),
            "format": "JSON",
        },
    )
    data = payload.get("data") or {}
    hits = data.get("hits") or []
    total = (data.get("pagination") or {}).get("total")
    if total is None:
        raise SystemExit(
            "GDC response carried no pagination total; refusing to "
            "guess whether the cohort is complete"
        )
    if len(hits) != total:
        raise SystemExit(
            f"GDC reports {total} cases but returned {len(hits)}; raise "
            f"--page-size above {total} rather than accepting a partial cohort"
        )
    if not hits:
        raise SystemExit(f"GDC has no cases for project {project_id}")

    cases = []
    for hit in hits:
        barcode = str(hit.get("submitter_id", "")).strip()
        case_id = str(hit.get("case_id", "")).strip()
        if not barcode or not case_id:
            raise SystemExit(f"GDC returned a case missing an identifier: {hit}")
        cases.append({"case_id": case_id, "submitter_id": barcode})

    barcodes = [case["submitter_id"] for case in cases]
    if len(set(barcodes)) != len(barcodes):
        raise SystemExit(
            "GDC returned a repeated barcode; the cohort would be "
            "ambiguous about which case a report belongs to"
        )
    return sorted(cases, key=lambda case: case["submitter_id"])


def digest(cases: list[dict[str, str]]) -> str:
    """Hash the cohort membership itself, so drift is detectable in one field.

    Over the sorted barcodes only: the digest has to answer "is this the same set
    of patients", so it must not change when the API reorders its hits or adds a
    field we do not use.
    """
    joined = "\n".join(case["submitter_id"] for case in cases)
    return hashlib.sha256(joined.encode()).hexdigest()


def read_existing(sidecar: Path) -> dict | None:
    """Read an earlier provenance sidecar, or None if there is none."""
    if not sidecar.is_file():
        return None
    return json.loads(sidecar.read_text(encoding="utf-8"))


def read_barcodes(path: Path) -> set[str]:
    """Read the submitter_id barcodes from an existing cohort file."""
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            value
            for row in csv.DictReader(handle, delimiter="\t")
            if (value := (row.get("submitter_id") or "").strip())
        }


def main() -> int:
    """Run the script; return the process exit status."""
    args = parse_args()
    sidecar_path = args.out.with_suffix(".provenance.json")

    status = get_json(STATUS_ENDPOINT)
    cases = fetch_cases(args.project_id, args.page_size)
    current = digest(cases)

    print(f"project                 : {args.project_id}")
    print(f"GDC data release        : {status.get('data_release')}")
    print(f"GDC API tag             : {status.get('tag')}")
    print(f"cases returned          : {len(cases)}")
    print(f"barcode digest          : {current[:16]}...")

    previous = read_existing(sidecar_path)
    if previous:
        before = previous.get("barcode_sha256")
        print(f"digest on disk          : {str(before)[:16]}...")
        if before == current:
            print("cohort unchanged        : yes")
        else:
            # Name the size of the change, not just its existence: one added case
            # and two hundred removed are different problems.
            old = read_barcodes(args.out) if args.out.is_file() else set()
            new = {case["submitter_id"] for case in cases}
            print(
                f"cohort unchanged        : NO -- {len(new - old)} added, "
                f"{len(old - new)} removed"
            )
            if not args.allow_cohort_change:
                print(
                    "refusing to overwrite. every label built against the old "
                    "cohort was built against a different set of patients."
                )
                print(
                    "re-run with --allow-cohort-change once that is understood, "
                    "and rebuild the roster and the document store after."
                )
                return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, delimiter="\t")
        writer.writeheader()
        writer.writerows(cases)

    sidecar = {
        "cohort": args.project_id,
        "endpoint": CASES_ENDPOINT,
        # Verbatim, so the query can be reissued by copying it rather than by
        # reconstructing it from prose.
        "filters": {
            "op": "in",
            "content": {
                "field": "cases.project.project_id",
                "value": [args.project_id],
            },
        },
        "fields": HEADER,
        "case_count": len(cases),
        "barcode_sha256": current,
        "gdc_data_release": status.get("data_release"),
        "gdc_api_tag": status.get("tag"),
        "gdc_api_commit": status.get("commit"),
        "retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "built_by": "scripts/endometrial_data/fetch_ucec_cohort.py",
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n")

    print()
    print(f"cohort     : {args.out}")
    print(f"provenance : {sidecar_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
