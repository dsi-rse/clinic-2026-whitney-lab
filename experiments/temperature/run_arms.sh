#!/usr/bin/env bash
# Run the four temperature arms (T0 once, T1 three times) against one GLM server.
#
# Start a server first (OncoTrace's running guide, or a sbatch with
# ONCOTRACE_HOLD_SERVER=1), wait for its endpoint.json, then run this inside tmux
# on the login node:
#
#   ONCOTRACE=~/oncotrace PY=~/envs/clinic-client/bin/python \
#     experiments/temperature/run_arms.sh <server job id> <endpoint.json> <runs folder>
#
# Each arm gets a fresh folder <runs folder>/<date>_temperature_<arm>. All four
# attach at once, 2 workers each: 8 requests in flight, the server's max_num_seqs.
# When every arm returns, it releases the server and writes each run's table and
# review. Run from the clinic repo root.
set -uo pipefail

JOB=$1
ENDPOINT=$2
RUNS=$3
OT=${ONCOTRACE:?set ONCOTRACE to your oncotrace checkout}
PY=${PY:?set PY to the clinic client python}
CONFIGS=$PWD/experiments/temperature/configs
DAY=$(date +%F)
ARMS="t0 t1_r1 t1_r2 t1_r3"

# The arm name before "_" is its config: t1_r2 uses configs/t1.yaml.
config() { echo "$CONFIGS/${1%%_*}.yaml"; }
folder() { echo "$RUNS/${DAY}_temperature_$1"; }

# An endpoint.json left by an older job would point at a dead server.
read -r EJOB BASE < <($PY -c 'import json, sys; d = json.load(open(sys.argv[1])); print(d["job_id"], d["base_url"])' "$ENDPOINT")
[ "$EJOB" = "$JOB" ] || { echo "endpoint.json names job $EJOB, not $JOB; wait for the new one"; exit 1; }

# OncoTrace skips any patient that already has a record, so never reuse a folder.
for arm in $ARMS; do
  [ -e "$(folder $arm)" ] && { echo "already exists, choose another runs folder: $(folder $arm)"; exit 1; }
done

for arm in $ARMS; do
  R=$(folder $arm)
  install -d -m 2750 "$R"
  cp "$(config $arm)" "$R/run_config.yaml"
  srun --jobid="$JOB" --overlap env PYTHONPATH="$OT" PYTHONNOUSERSITE=1 \
    "$PY" -m oncotrace.runner extract --config "$(config $arm)" --output "$R" \
      --base-url "$BASE" --workers 2 > "$R/client.out" 2>&1 &
done
echo "$(date -Is) attached $ARMS to $BASE"
wait

for arm in $ARMS; do
  echo "$arm: $(ls "$(folder $arm)/units" | wc -l) records"
done
echo "$(date -Is) all arms returned; releasing job $JOB"
scancel "$JOB"

for arm in $ARMS; do
  R=$(folder $arm)
  PYTHONPATH="$OT" PYTHONNOUSERSITE=1 "$PY" -m oncotrace.runner table --config "$(config $arm)" --output "$R" > "$R/table.out" 2>&1
  PYTHONPATH="$OT" PYTHONNOUSERSITE=1 "$PY" -m oncotrace.runner review --config "$(config $arm)" --output "$R" > "$R/review.out" 2>&1
  # OncoTrace's umask 077 leaves record files owner-only despite group_readable.
  chmod -R g+rX "$R"
done
echo "$(date -Is) done"
