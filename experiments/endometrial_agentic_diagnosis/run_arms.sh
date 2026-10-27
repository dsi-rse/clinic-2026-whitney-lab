#!/usr/bin/env bash
# Serve the model once, then run each experiment arm against that one server.
#
# Every arm writes to its own folder, <OUTPUT>/<arm>, and arms run one after another so
# they do not share a batch. The arms differ from base.yaml in one setting each (see
# make_arms.py). Arms are listed most important first, so if the time limit cuts the job
# short the finished arms are still usable and a resubmission resumes the rest.
#
# Required environment (set by run_arms.sbatch): ONCOTRACE_REPO, ONCOTRACE_OUTPUT,
# ONCOTRACE_PYTHON. Optional: ARMS (space-separated), ONCOTRACE_WORKERS (default 3).
set -uo pipefail
umask 077

REPO=${ONCOTRACE_REPO:?}
OUTPUT=${ONCOTRACE_OUTPUT:?}
PY=${ONCOTRACE_PYTHON:?}
WORKERS=${ONCOTRACE_WORKERS:-3}
# tokens16k is left out by default: the reply-cap test is already proposed by another
# experiment (endometrial_failure_modes) and needs agreeing with its author first.
ARMS=${ARMS:-"compact calls6 norule calls12 read6k"}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# serve_and_label reads configs relative to the OncoTrace repo
rel() { realpath --relative-to="$REPO" "$HERE/$1"; }

say() { echo "[$(date -u +%FT%TZ)] $*"; }
export PYTHONNOUSERSITE=1 PYTHONPATH="$REPO"
cd "$REPO"
install -d -m 700 -- "$OUTPUT"
rm -f "$OUTPUT/endpoint.json"

# Check every arm before the slow weight load, so a typo fails in seconds.
for arm in $ARMS; do
  "$PY" -m oncotrace.runner check --config "$(rel "arm_$arm.yaml")" --output "$OUTPUT" > /dev/null \
    || { say "config check failed for arm $arm"; exit 1; }
done

say "serving on $(hostname)"
"$PY" -m oncotrace.runner serve --config "$(rel base.yaml)" --output "$OUTPUT" &
SERVER=$!
trap 'kill -TERM "$SERVER" 2>/dev/null' EXIT

DEADLINE=$(( SECONDS + 7200 ))
while [[ ! -s "$OUTPUT/endpoint.json" ]]; do
  kill -0 "$SERVER" 2>/dev/null || { say "server exited before publishing an endpoint"; exit 1; }
  (( SECONDS < DEADLINE )) || { say "no endpoint after two hours"; exit 1; }
  sleep 20
done
BASE=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_url"])' "$OUTPUT/endpoint.json")
say "endpoint ready at $BASE after ${SECONDS}s"

status=0
for arm in $ARMS; do
  say "arm $arm"
  "$PY" -m oncotrace.runner extract \
    --config "$(rel "arm_$arm.yaml")" --output "$OUTPUT/$arm" --base-url "$BASE" --workers "$WORKERS"
  rc=$?
  say "arm $arm returned rc=$rc"
  (( rc == 0 )) || status=$rc
done
exit "$status"
