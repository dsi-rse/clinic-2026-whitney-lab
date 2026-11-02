#!/usr/bin/env bash
# Repeated extraction (clinic issue 17): one GLM server, REPEATS identical extractions.
# Derived from OncoTrace's endometrial_dsi.sbatch; read the resource comments below
# before changing them. Every path comes from the environment, none is personal:
#
#   ONCOTRACE_REPO=/path/to/oncotrace ONCOTRACE_PYTHON=/path/to/client/bin/python \
#   ONCOTRACE_CONFIG=/path/to/default.yaml ONCOTRACE_OUTPUT=/path/to/new/run_folder \
#   DETERMINISM_DRIVER=/path/to/run_repeats.sh REPEATS=5 \
#     sbatch --output=/path/to/new/run_folder/job_logs/job-%j.out \
#     experiments/endometrial_determinism/run_repeats.sbatch
#
# Create the --output folder first: Slurm will not create it.
#
#SBATCH --job-name=repeats-glm
#SBATCH --partition=general
#SBATCH --qos=general
#SBATCH --gres=gpu:h200:4,local:disk:100G
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH --time=12:00:00
#SBATCH --open-mode=append
#
# Why these values, on this cluster (measured 2026-09-10, see
# docs/dsi-cluster.md):
#
#   partition  `general` is where every GPU node lives, including all of the
#              H200s. `dev` is capped at 10 minutes, which is shorter than this
#              model's weight load.
#   qos        `general` is the default tier. Do NOT use `protected`: it caps
#              at 2 hours, so a preemption or a slow unstaged load eats the
#              window before any unit record exists. `interactive` (4 h) can
#              preempt `general` jobs, so expect eviction and rely on per-unit
#              resume.
#   gres       The type name here is plain `h200`, not a memory-suffixed name.
#              Nodes: p001-p003 and o001/q001 carry 4 each, r001-r003 carry 8.
#              A bare --gres=gpu:4 can land on a40 (48 GB) or a100 (80 GB),
#              where this config does not fit. `local:disk` is requested in the
#              same list because that request is what creates the node-local
#              scratch directory below - see the TMPDIR note.
#   mem        200G with no CPU offload. p00x nodes have 773 GB, the r00x nodes
#              2 TB, so this is comfortable.
#   time       3 hours. One hour is enough for the Qwen3 config; the larger
#              GLM-5.3-Flash run keeps room for checkpoint variation and useful
#              extraction after startup. The partition maximum is 12 hours.
#
# Unlike CRI, this cluster's /tmp is exec-capable (verified by dlopen on p001),
# so the noexec JIT failure does not occur here. TMPDIR still moves off it,
# because /tmp is not a separate filesystem: it sits on the 98 GB root volume
# (45 GB free on p001) shared with every other job on the node.
#
# The node-local NVMe is /local/scratch (894 GB, /dev/nvme0n1). Two things
# about it are easy to get wrong, both measured on p001 on 2026-09-10:
#
#   - /local/scratch is root-owned mode 1775, so you cannot mkdir in it. Slurm
#     creates /local/scratch/$USER_$SLURM_JOB_ID for you, mode 700, and removes
#     it when the job ends.
#   - **It only does that if the job requested the `local:disk` GRES.** Without
#     it the directory simply does not exist, and a script that assumes it gets
#     `No such file or directory`. Verified both ways: job 1657989 asked for
#     local:disk:100G and had the directory; job 1658061 did not ask and did
#     not.
#
# /local itself is world-writable and sticky, but it is on that same 98 GB root
# volume, so it is not the right place for a JIT workspace either.
set -uo pipefail
umask 077

# Required: no personal paths as defaults. Optional: ONCOTRACE_SERVING_IMAGE (a
# squashfs of the serving environment to stage onto node-local NVMe; when it is
# unset the server starts from serving_root directly).
REPO=${ONCOTRACE_REPO:?set ONCOTRACE_REPO to your oncotrace checkout}
CONFIG=${ONCOTRACE_CONFIG:?set ONCOTRACE_CONFIG to the run config}
OUTPUT=${ONCOTRACE_OUTPUT:?set ONCOTRACE_OUTPUT to the run folder}
DRIVER=${DETERMINISM_DRIVER:?set DETERMINISM_DRIVER to run_repeats.sh}
PY=${ONCOTRACE_PYTHON:?set ONCOTRACE_PYTHON to the client python}
IMAGE=${ONCOTRACE_SERVING_IMAGE:-}

cd "$REPO" || { echo "cannot cd to $REPO" >&2; exit 1; }
# serve_and_label_slurm.sh reads $REPO/$CONFIG, so the config must be relative
# to the repo. Accept an absolute path and convert it.
case "$CONFIG" in /*) CONFIG=$(realpath --relative-to="$REPO" "$CONFIG") ;; esac
[[ -x "$PY" ]]     || { echo "client python not executable: $PY" >&2; exit 1; }
[[ -f "$CONFIG" ]] || { echo "config not found: $CONFIG (run from the repo root)" >&2; exit 1; }

export PYTHONNOUSERSITE=1 PYTHONPATH="$REPO"
# Node-local scratch on the NVMe. Slurm made this directory because of the
# local:disk GRES above and will remove it at job exit, so there is no cleanup
# trap here. Fail loudly if it is missing rather than silently falling back to
# the root volume: a JIT workspace that fills / takes the whole node with it.
export TMPDIR=/local/scratch/${USER}_${SLURM_JOB_ID}
if [ ! -d "$TMPDIR" ]; then
  echo "=== ABORT: $TMPDIR does not exist ==="
  echo "Slurm creates it only for jobs that request the local:disk GRES."
  echo "Check that --gres still includes local:disk (see the header)."
  exit 2
fi
install -d -m 700 -- "$OUTPUT"

run_extract() {
  if [ -z "$IMAGE" ]; then
    "$PY" -m oncotrace.runner extract \
      --config "$CONFIG" --output "$OUTPUT" --serve --workers 3
    return
  fi

  [[ -s "$IMAGE" ]] || { echo "serving image not found: $IMAGE" >&2; return 2; }
  [[ -s "$IMAGE.fingerprint" ]] || {
    echo "serving image fingerprint not found: $IMAGE.fingerprint" >&2
    return 2
  }
  command -v bwrap >/dev/null || { echo "bwrap is required for staging" >&2; return 2; }
  command -v unsquashfs >/dev/null || {
    echo "unsquashfs is required for staging" >&2
    return 2
  }

  local serving_root
  serving_root=$("$PY" - "$CONFIG" <<'PYEOF'
import sys

import yaml

with open(sys.argv[1]) as handle:
    print(yaml.safe_load(handle)["serving"]["serving_root"])
PYEOF
  ) || return
  [[ -d "$serving_root" ]] || {
    echo "configured serving root not found: $serving_root" >&2
    return 2
  }

  local fingerprint
  fingerprint=$(
    {
      find "$serving_root/conda-meta" -maxdepth 1 -type f -name '*.json' -printf '%f\n'
      find "$serving_root"/lib/python3.*/site-packages \
        -maxdepth 1 -type d -name '*.dist-info' -printf '%f\n'
      find "$serving_root"/lib/python3.*/site-packages \
        -maxdepth 1 -type f -name '*.pth' -printf '%f\n'
    } | LC_ALL=C sort | sha256sum | cut -d' ' -f1
  ) || return
  if [ "$(tr -d '[:space:]' < "$IMAGE.fingerprint")" != "$fingerprint" ]; then
    echo "serving image is stale for configured root: $serving_root" >&2
    echo "rebuild it with scripts/build_serving_image_dsi.sbatch" >&2
    return 2
  fi
  echo "serving image: $IMAGE"
  echo "serving image fingerprint: $fingerprint"

  local local_root=$TMPDIR/serving-env
  local local_image=$TMPDIR/serving-env.sqfs
  local started copied extracted
  started=$(date +%s)
  cp -- "$IMAGE" "$local_image" || return
  copied=$(date +%s)
  unsquashfs -f -d "$local_root" "$local_image" >/dev/null || return
  extracted=$(date +%s)
  echo "serving image copy: $((copied-started))s; extract: $((extracted-copied))s"

  # The private mount keeps the configured prefix visible to vLLM and its JIT
  # cache while the files at that prefix come from node-local NVMe.
  #
  # Inside the mount this runs serve_and_label_slurm.sh rather than
  # `extract --serve`. Both put a server and a client in one allocation, but
  # `--serve` ties the server's life to one extraction: a client that fails on a
  # bad limit or a config typo takes the whole weight load with it, and on this
  # cluster that is the better part of an hour. Splitting them lets the server
  # outlive a failed client, so a second attempt costs nothing. That script owns
  # the endpoint handshake - publish, wait, dial over loopback - and is the only
  # copy of it.
  bwrap --die-with-parent \
    --bind / / \
    --dev-bind /dev /dev \
    --bind "$local_root" "$serving_root" \
    env ONCOTRACE_REPO="$REPO" \
        ONCOTRACE_CONFIG="$CONFIG" \
        ONCOTRACE_OUTPUT="$OUTPUT" \
        ONCOTRACE_RUN="$OUTPUT" \
        ONCOTRACE_WORKERS="${ONCOTRACE_WORKERS:-3}" \
        REPEATS="${REPEATS:-5}" \
        ONCOTRACE_PYTHON="$PY" \
      "$DRIVER"
}

echo "=== oncotrace endometrial: job ${SLURM_JOB_ID:-none} on $(hostname -s) at $(date -Is) ==="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
N=$(nvidia-smi -L | wc -l)
echo "visible GPUs: $N"
if [ "$N" -lt 4 ]; then
  echo "=== ABORT: got $N GPUs, tensor_parallel_size=4 needs 4 ==="
  exit 2
fi

echo "--- serve + attach one client in this allocation ---"
run_extract
rc=$?
if [ $rc -ne 0 ]; then
  echo "=== serve+client FAILED rc=$rc; last lines of $OUTPUT/server.log ==="
  tail -60 "$OUTPUT/server.log" 2>/dev/null
  exit $rc
fi

echo "=== determinism repeats complete at $(date -Is); runs under $OUTPUT/rep* ==="
