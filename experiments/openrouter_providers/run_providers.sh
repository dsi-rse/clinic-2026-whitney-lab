#!/usr/bin/env bash
# Run each provider arm REPEATS times on OpenRouter, the three arms side by side.
#
# Each repeat writes to its own folder, <RUNS>/<DATE>_openrouter_providers_<arm>/rep1
# ... repN, so no repeat can resume from or overwrite another.
#
# Run from the clinic repo root, with the data built by
# scripts/endometrial_data/download.sh and OPENROUTER_API_KEY set (e.g. from .env):
#   set -a; source .env; set +a
#   RUNS=runs ONCOTRACE_REPO=~/oncotrace PYTHON=python \
#     bash experiments/openrouter_providers/run_providers.sh
# Optional: REPEATS (default 3), WORKERS (patients at once per arm, default 5),
# DATE (default today), ARMS (config names, default: wafer_us darkbloom_fp4 morph_fp8).
set -uo pipefail
umask 027

RUNS=${RUNS:?set RUNS to the folder that will hold the run folders}
REPO=${ONCOTRACE_REPO:?set ONCOTRACE_REPO to your OncoTrace clone}
PY=${PYTHON:-python}
REPEATS=${REPEATS:-3}
WORKERS=${WORKERS:-5}
DATE=${DATE:-$(date +%F)}
: "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY}"
CONFIGS=experiments/openrouter_providers/configs
export PYTHONPATH="$REPO"

say() { echo "[$(date -u +%FT%TZ)] $*"; }
say "code: oncotrace $(git -C "$REPO" rev-parse HEAD) (uncommitted: $(git -C "$REPO" status --porcelain --untracked-files=no | wc -l)); clinic $(git rev-parse HEAD) (uncommitted: $(git status --porcelain --untracked-files=no | wc -l))"

run_arm() {
  local arm=$1 out="$RUNS/${DATE}_openrouter_providers_$1" rc=0
  for i in $(seq 1 "$REPEATS"); do
    if [[ -e "$out/rep$i" ]]; then
      say "$arm: $out/rep$i already exists; use a new DATE rather than reusing a run folder"
      return 1
    fi
    say "$arm: repeat $i of $REPEATS"
    "$PY" -m oncotrace.runner extract --config "$CONFIGS/$arm.yaml" \
      --output "$out/rep$i" --workers "$WORKERS" > "$out.rep$i.log" 2>&1 || rc=$?
    say "$arm: repeat $i returned rc=$rc"
  done
  return "$rc"
}

mkdir -p "$RUNS"
status=0
for arm in ${ARMS:-wafer_us darkbloom_fp4 morph_fp8}; do
  run_arm "$arm" &
done
for job in $(jobs -p); do
  wait "$job" || status=1
done
exit "$status"
