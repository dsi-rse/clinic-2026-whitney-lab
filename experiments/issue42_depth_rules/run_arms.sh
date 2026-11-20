#!/usr/bin/env bash
# Run the issue #42 extractions on OpenRouter, one new run folder per arm.
#
# Usage, from the clinic repo root (the key must be in the environment):
#
#   set -a; source .env; set +a
#   ONCOTRACE=~/oncotrace PYTHON=python \
#     bash experiments/issue42_depth_rules/run_arms.sh <runs dir> <date> <arm>...
#
# An arm name picks its config by its first two parts:
#   old_t0_a, old_t0_b, new_t0   -> configs/old_t0.yaml or configs/new_t0.yaml
#   old_t1_rep01 ... new_t1_rep20 -> configs/old_t1.yaml or configs/new_t1.yaml
# Each arm writes <runs dir>/<date>_issue42_<arm>/ and a .log beside it. An
# existing folder is never reused: the script stops instead.
#
# WORKERS (default 5) is the number of patients extracted at once within an arm.
# Keep it at 5 or less: other sessions share the same OpenRouter provider.
set -euo pipefail

runs_dir=$1
date=$2
shift 2
here=$(cd "$(dirname "$0")" && pwd)
workers=${WORKERS:-5}
: "${ONCOTRACE:?set ONCOTRACE to an OncoTrace checkout}"
: "${OPENROUTER_API_KEY:?load the key first: set -a; source .env; set +a}"
python=${PYTHON:-python}

for arm in "$@"; do
    config="$here/configs/$(echo "$arm" | cut -d_ -f1-2).yaml"
    out="$runs_dir/${date}_issue42_${arm}"
    if [ ! -f "$config" ]; then
        echo "no config for arm $arm: $config" >&2
        exit 1
    fi
    if [ -e "$out" ]; then
        echo "$out already exists; use a new folder" >&2
        exit 1
    fi
    echo "$(date '+%H:%M:%S') $arm -> $out"
    PYTHONPATH="$ONCOTRACE" "$python" -m oncotrace.runner extract \
        --config "$config" --output "$out" --workers "$workers" \
        > "$out.log" 2>&1
done
