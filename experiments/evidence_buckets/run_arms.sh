#!/usr/bin/env bash
# Run the baseline and evidence arms on OpenRouter, REPEATS times each.
#
# The two arms run side by side, so a change on the provider's side during the
# runs affects both alike; each arm runs its repeats one after another. Every
# repeat writes to its own new folder, <RUNS>/<DATE>_evidence_buckets_<arm>/repN,
# because OncoTrace resumes a folder that already holds records.
#
# Run from the clinic repo root, with the data built by
# scripts/endometrial_data/download.sh and OPENROUTER_API_KEY set:
#   set -a; source .env; set +a
#   RUNS=runs ONCOTRACE_REPO=~/oncotrace PYTHON=python \
#     bash experiments/evidence_buckets/run_arms.sh
# Optional: REPEATS (default 2), WORKERS (patients at once per arm, default 2),
# DATE (default today).
set -uo pipefail
umask 027

RUNS=${RUNS:?set RUNS to the folder that will hold the run folders}
REPO=${ONCOTRACE_REPO:?set ONCOTRACE_REPO to your OncoTrace clone}
PY=${PYTHON:-python}
REPEATS=${REPEATS:-2}
WORKERS=${WORKERS:-2}
DATE=${DATE:-$(date +%F)}
: "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY}"
CONFIGS=experiments/evidence_buckets/configs
export PYTHONPATH="$REPO"

say() { echo "[$(date -u +%FT%TZ)] $*"; }
say "code: oncotrace $(git -C "$REPO" rev-parse HEAD) (uncommitted: $(git -C "$REPO" status --porcelain --untracked-files=no | wc -l)); clinic $(git rev-parse HEAD) (uncommitted: $(git status --porcelain --untracked-files=no | wc -l))"

run_arm() {
  local arm=$1 out="$RUNS/${DATE}_evidence_buckets_$1" rc=0
  for i in $(seq 1 "$REPEATS"); do
    if [[ -e "$out/rep$i" ]]; then
      say "$arm: $out/rep$i already exists; use a new DATE rather than reusing a run folder"
      return 1
    fi
    mkdir -p "$out"
    say "$arm: repeat $i of $REPEATS"
    "$PY" -m oncotrace.runner extract --config "$CONFIGS/$arm.yaml" \
      --output "$out/rep$i" --workers "$WORKERS" > "$out/rep$i.log" 2>&1 || rc=$?
    say "$arm: repeat $i returned rc=$rc"
    "$PY" -m oncotrace.runner table --config "$CONFIGS/$arm.yaml" \
      --output "$out/rep$i" > "$out/rep$i.table.log" 2>&1
  done
  return "$rc"
}

mkdir -p "$RUNS"
status=0
for arm in baseline evidence; do
  run_arm "$arm" &
done
for job in $(jobs -p); do
  wait "$job" || status=1
done
say "all arms returned, status $status"
exit "$status"
