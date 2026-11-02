#!/usr/bin/env bash
# Remake every result table of this experiment from the shared run folders.
#
# Needs: RUNS (the folder that holds the run folders), ONCOTRACE_F99CEFD and
# ONCOTRACE_0B6F404 (OncoTrace checkouts at those commits; only TraceView's
# scoring.py is read), and a Python with httpx, pyyaml and pydantic.
# Run from the clinic repo root with PYTHONPATH=src. Pass a prefix for the result
# folders, for example: bash experiments/endometrial_determinism/run_analysis.sh $(date +%F_%H%M%S)
set -euo pipefail
: "${RUNS:?set RUNS to the folder that holds the run folders}"
: "${ONCOTRACE_F99CEFD:?set ONCOTRACE_F99CEFD to an OncoTrace checkout at f99cefd}"
: "${ONCOTRACE_0B6F404:?set ONCOTRACE_0B6F404 to an OncoTrace checkout at 0b6f404}"
STAMP=${1:?give a prefix for the result folders, e.g. 2026-11-02_091755}
PYTHON=${PYTHON:-python3}
export PYTHONDONTWRITEBYTECODE=1
D=experiments/endometrial_determinism
R5=$RUNS/2026-10-25_determinism_5x
R10=$RUNS/2026-10-28_followup_10x10
R20=$RUNS/2026-10-30_followup_10x20_main0b6f404

"$PYTHON" $D/analyze_repeats.py --reps-dir "$R5" --label "${STAMP}_agentic_f99cefd_50x5" \
  --job 2239457 --job 2244400 \
  --job-log "$R5/job_logs/determinism-2239457.out" --job-log "$R5/job_logs/determinism-2244400.out" \
  --server-log "$R5/server.log" --oncotrace "$ONCOTRACE_F99CEFD" \
  --input config=$D/default.yaml --input roster=$D/roster_annotated50.csv
"$PYTHON" $D/analyze_repeats.py --reps-dir "$R10" --label "${STAMP}_agentic_f99cefd_10x10" \
  --job 2260881 --job 2267023 \
  --job-log "$R10/job_logs/determinism-2260881.out" --job-log "$R10/job_logs/determinism-2267023.out" \
  --server-log "$R10/server.log" --oncotrace "$ONCOTRACE_F99CEFD" \
  --input config=$D/followup10.yaml --input roster=$D/roster_followup10.csv
"$PYTHON" $D/analyze_repeats.py --reps-dir "$R20" --label "${STAMP}_agentic_0b6f404_10x20" \
  --job 2284447 --job 2286351 --job 2287510 --job 2287759 \
  --job-log "$R20/job_logs/baseline_full-2284447.out" --job-log "$R20/job_logs/baseline_full-2286351.out" \
  --job-log "$R20/job_logs/baseline_full-2287510.out" --job-log "$R20/job_logs/baseline_full-2287759.out" \
  --server-log "$R20/server.log" --oncotrace "$ONCOTRACE_0B6F404" \
  --input config=$D/followup10_new_version.yaml --input roster=$D/roster_followup10.csv
"$PYTHON" $D/repeat_matrix.py --group old_f99cefd_10x10="$R10" --group new_0b6f404_10x20="$R20" \
  --patients-csv $D/roster_followup10.csv --out "$D/results/${STAMP}_repeat_matrix_old_vs_new_10_patients"
