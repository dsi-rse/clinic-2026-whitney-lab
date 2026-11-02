#!/usr/bin/env bash
# Keep exactly one protected-QOS job (2 h) in the queue until every patient has a record.
#
# `protected` allows one job at a time, so a chain cannot be queued ahead. This loop
# submits the next job when none is queued or running. A resubmit resumes: patients that
# already have a record are skipped. It stops when all patients are done or after MAX
# submissions, so a job that keeps failing cannot loop forever.
#
# Required environment: ONCOTRACE_REPO (oncotrace checkout), ONCOTRACE_PYTHON (client python).
# Optional: CONFIG (default: full_agentic.yaml next to this script), REPEATS (default 1),
# JOB_NAME, EXCLUDE (comma-separated nodes to avoid), ONCOTRACE_SERVING_IMAGE.
#
# Usage: keep_one_protected_job.sh OUTPUT_FOLDER [TOTAL_RECORDS] [MAX_SUBMISSIONS]
set -uo pipefail

OUT=${1:?output folder}
TOTAL=${2:-546}
MAX=${3:-8}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=${ONCOTRACE_REPO:?set ONCOTRACE_REPO to your oncotrace checkout}
: "${ONCOTRACE_PYTHON:?set ONCOTRACE_PYTHON to the client python}"
CONFIG=${CONFIG:-$HERE/full_agentic.yaml}
SBATCH=$HERE/run_extraction.sbatch
DRIVER=$HERE/run_extraction.sh

say() { echo "[$(date -Is)] $*"; }
records() { find "$OUT" -path '*/rep*/units/*.json' 2>/dev/null | wc -l; }

mkdir -p "$OUT/job_logs"
submitted=0
while (( $(records) < TOTAL )); do
  if [[ -z "$(squeue -u "$USER" -h -q protected -o %i)" ]]; then
    if (( submitted >= MAX )); then say "stopping: $MAX submissions used, $(records)/$TOTAL done"; exit 1; fi
    job=$(cd "$REPO" && sbatch --parsable --qos=protected --time=02:00:00 \
      ${EXCLUDE:+--exclude="$EXCLUDE"} --cpus-per-task=32 --job-name="${JOB_NAME:-baseline-prot}" \
      --output="$OUT/job_logs/baseline_full-%j.out" \
      --export=ALL,ONCOTRACE_REPO="$REPO",ONCOTRACE_CONFIG="$CONFIG",ONCOTRACE_OUTPUT="$OUT",REPEATS="${REPEATS:-1}",EXTRACT_DRIVER="$DRIVER" \
      "$SBATCH") || { say "sbatch failed"; sleep 300; continue; }
    submitted=$((submitted + 1))
    say "submitted $job ($submitted of $MAX), $(records)/$TOTAL records"
  fi
  sleep 120
done
say "all $TOTAL patients have a record"
