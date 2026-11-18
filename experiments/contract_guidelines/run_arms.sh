#!/usr/bin/env bash
# Run each contract arm REPEATS times on the 66 annotated patients, on OpenRouter.
#
# Runs go one at a time, alternating arms (old, unguided, guided, old, ...), so
# no arm gets all the quiet or all the busy hours. Each run writes to its own
# new folder, <RUNS>/<DATE>_contract_guidelines_<arm>_r<i>; an existing folder
# stops the script rather than being resumed.
#
# Run from the clinic repo root, with the data built by
# scripts/endometrial_data/download.sh and OPENROUTER_API_KEY set:
#   set -a; source .env; set +a
#   RUNS=runs ONCOTRACE_REPO=~/oncotrace PYTHON=python \
#     bash experiments/contract_guidelines/run_arms.sh
# Optional: REPEATS (default 2), WORKERS (patients at once, default 5),
# DATE (default today), ARMS (default: old unguided guided).
set -uo pipefail
umask 027

RUNS=${RUNS:?set RUNS to the folder that will hold the run folders}
REPO=${ONCOTRACE_REPO:?set ONCOTRACE_REPO to your OncoTrace clone}
PY=${PYTHON:-python}
REPEATS=${REPEATS:-2}
WORKERS=${WORKERS:-5}
DATE=${DATE:-$(date +%F)}
: "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY}"
CONFIGS=experiments/contract_guidelines/configs
export PYTHONPATH="$REPO"

say() { echo "[$(date -u +%FT%TZ)] $*"; }
say "code: oncotrace $(git -C "$REPO" rev-parse HEAD) (uncommitted: $(git -C "$REPO" status --porcelain --untracked-files=no | wc -l)); clinic $(git rev-parse HEAD) (uncommitted: $(git status --porcelain --untracked-files=no | wc -l))"

mkdir -p "$RUNS"
status=0
for i in $(seq 1 "$REPEATS"); do
  for arm in ${ARMS:-old unguided guided}; do
    out="$RUNS/${DATE}_contract_guidelines_${arm}_r$i"
    if [[ -e "$out" ]]; then
      say "$out already exists; use a new DATE rather than reusing a run folder"
      exit 1
    fi
    say "$arm: repeat $i of $REPEATS"
    rc=0
    "$PY" -m oncotrace.runner extract --config "$CONFIGS/$arm.yaml" \
      --output "$out" --workers "$WORKERS" > "$out.log" 2>&1 || rc=$?
    say "$arm: repeat $i returned rc=$rc"
    [[ $rc -eq 0 ]] || status=1
  done
done
exit "$status"
