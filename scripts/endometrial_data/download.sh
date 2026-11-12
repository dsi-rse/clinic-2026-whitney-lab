#!/usr/bin/env bash
# Build the endometrial report store on your own machine from public data, then
# check it is identical to the shared copy. See docs/local-data.md.
#
# Usage, from the repository root:
#   ONCOTRACE_REPO=~/oncotrace bash scripts/endometrial_data/download.sh
set -euo pipefail

cd "$(dirname "$0")/../.."
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi
export DATA_DIR="${DATA_DIR:-./data}"
export ONCOTRACE_REPO="${ONCOTRACE_REPO:-$HOME/oncotrace}"
PYTHON="${PYTHON:-python}"
OUT="$DATA_DIR/endometrial"
ARCHIVE="$OUT/downloads/aws_response.tar.gz"
ARCHIVE_URL="https://tatonettilab-resources.s3.us-west-1.amazonaws.com/tcga-path-reports/aws_response.tar.gz"
ARCHIVE_BYTES=774511262

[[ -f "$ONCOTRACE_REPO/oncotrace/records.py" ]] || {
  echo "Set ONCOTRACE_REPO to your OncoTrace clone (the store is checked with its reader)." >&2
  exit 1
}

echo "1/5  Asking the GDC which patients are in TCGA-UCEC"
"$PYTHON" scripts/endometrial_data/fetch_ucec_cohort.py

echo "2/5  Downloading the OCR archive (775 MB, once)"
mkdir -p "$OUT/downloads"
if [[ ! -f "$ARCHIVE" || "$(wc -c < "$ARCHIVE" | tr -d ' ')" != "$ARCHIVE_BYTES" ]]; then
  curl -fL --retry 3 -o "$ARCHIVE.part" "$ARCHIVE_URL"
  mv "$ARCHIVE.part" "$ARCHIVE"
fi
[[ "$(wc -c < "$ARCHIVE" | tr -d ' ')" == "$ARCHIVE_BYTES" ]] || {
  echo "The archive is not the expected size; delete it and run again." >&2
  exit 1
}

echo "3/5  Pulling out the endometrial pages"
"$PYTHON" scripts/endometrial_data/extract_ocr_pages.py

echo "4/5  Building the roster and the report store"
"$PYTHON" scripts/endometrial_data/build_ucec_sources.py
"$PYTHON" scripts/endometrial_data/build_ucec_document_store.py

echo "5/5  Checking the result against the shared copy"
"$PYTHON" scripts/endometrial_data/verify_store.py

echo
echo "Done. Point your config at:"
echo "  roster: $OUT/roster_ucec.csv"
echo "  store : $OUT/documents/ucec_pathology_report.jsonl"
