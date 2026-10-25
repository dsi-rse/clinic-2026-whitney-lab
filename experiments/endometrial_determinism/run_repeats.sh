#!/usr/bin/env bash
# Serve the model once, then run the same extraction N times against that server.
#
# Each repeat writes to its own folder, <OUTPUT>/rep1 ... repN, so no repeat can
# resume from or overwrite another. All repeats share one server, so any
# difference between them is not a difference in how the server was started.
#
# Required environment (set by run_repeats.sbatch): ONCOTRACE_REPO,
# ONCOTRACE_CONFIG (relative to the repo), ONCOTRACE_OUTPUT, ONCOTRACE_PYTHON.
# Optional: REPEATS (default 5), ONCOTRACE_WORKERS (default 3).
set -uo pipefail
umask 077

REPO=${ONCOTRACE_REPO:?}
CONFIG=${ONCOTRACE_CONFIG:?}
OUTPUT=${ONCOTRACE_OUTPUT:?}
PY=${ONCOTRACE_PYTHON:?}
WORKERS=${ONCOTRACE_WORKERS:-3}
REPEATS=${REPEATS:-5}

say() { echo "[$(date -u +%FT%TZ)] $*"; }
export PYTHONNOUSERSITE=1 PYTHONPATH="$REPO"
cd "$REPO"
install -d -m 700 -- "$OUTPUT"
rm -f "$OUTPUT/endpoint.json"

"$PY" -m oncotrace.runner check --config "$CONFIG" --output "$OUTPUT" || exit 1

say "serving on $(hostname)"
"$PY" -m oncotrace.runner serve --config "$CONFIG" --output "$OUTPUT" &
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
for i in $(seq 1 "$REPEATS"); do
  say "repeat $i of $REPEATS"
  "$PY" -m oncotrace.runner extract \
    --config "$CONFIG" --output "$OUTPUT/rep$i" --base-url "$BASE" --workers "$WORKERS"
  rc=$?
  say "repeat $i returned rc=$rc"
  (( rc == 0 )) || status=$rc
done
exit "$status"
