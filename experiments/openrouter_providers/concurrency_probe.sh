#!/usr/bin/env bash
# How many patients can run at once on wafer/us before OpenRouter refuses requests?
#
# Runs the 66 annotated patients once per level in LEVELS (patients at a time),
# each into its own folder <RUNS>/<DATE>_openrouter_concurrency_w<level>. Stops
# raising the level after the first one where any request was refused (OncoTrace
# logs "request failed" for every retry) or any patient ended in a server error.
#
# Run from the clinic repo root with OPENROUTER_API_KEY set:
#   set -a; source .env; set +a
#   RUNS=runs ONCOTRACE_REPO=~/oncotrace PYTHON=python \
#     bash experiments/openrouter_providers/concurrency_probe.sh
# Optional: LEVELS (default "10 20 40"), DATE (default today).
set -uo pipefail
umask 027

RUNS=${RUNS:?set RUNS to the folder that will hold the run folders}
REPO=${ONCOTRACE_REPO:?set ONCOTRACE_REPO to your OncoTrace clone}
PY=${PYTHON:-python}
LEVELS=${LEVELS:-10 20 40}
DATE=${DATE:-$(date +%F)}
: "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY}"
CONFIG=experiments/openrouter_providers/configs/wafer_us_annotated66.yaml
export PYTHONPATH="$REPO"

say() { echo "[$(date -u +%FT%TZ)] $*"; }
say "code: oncotrace $(git -C "$REPO" rev-parse HEAD) (uncommitted: $(git -C "$REPO" status --porcelain --untracked-files=no | wc -l)); clinic $(git rev-parse HEAD) (uncommitted: $(git status --porcelain --untracked-files=no | wc -l))"
mkdir -p "$RUNS"
for level in $LEVELS; do
  out="$RUNS/${DATE}_openrouter_concurrency_w$level"
  if [[ -e "$out" ]]; then
    say "$out already exists; use a new DATE rather than reusing a run folder"
    exit 1
  fi
  say "level $level: start"
  "$PY" -m oncotrace.runner extract --config "$CONFIG" --output "$out" \
    --workers "$level" > "$out.log" 2>&1
  rc=$?
  refused=$(grep -c "request failed" "$out.log")
  say "level $level: rc=$rc, refused requests logged: $refused"
  if (( rc != 0 || refused > 0 )); then
    say "stopping: level $level had failures"
    break
  fi
done
