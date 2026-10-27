# Does sampling temperature change OncoTrace's answers?

**Question:** every endometrial run so far uses temperature 0.0 / top_p 1.0. GLM-5.3-Flash's own `generation_config.json` uses 1.0 / 0.95. Does the higher setting change accuracy, how many model calls and tokens a patient takes, or the model's stated confidence?

**Why it matters:** if temperature 1.0 were more accurate, or made the model abstain on ambiguous reports (#13), every experiment should move to it. If it changes nothing, temperature 0 stays the default, and over-commitment has to be fixed some other way.

**Short answer (results: [`results/2026-10-25_152031/`](results/2026-10-25_152031/README.md)):**
- **Accuracy and confidence did not change.** Invasion agreed with the annotations in 47/50 patients in every run, and depth in 38/50 (37 in one T1 repeat). Confidence was `high` in 46–49 of 50 at both settings.
- **Temperature 1.0 costs more.** The median stays at 4 model calls, but the mean rises from 4.1 to 4.7–5.2, and the longest patient goes from 11 to 15–22 calls. Completion tokens rise about 20% per patient (median).
- **Over-commitment is not a sampling effect.** The 11 #13 patients the annotations leave undetermined got the same definite depth answer in all 4 runs. T1 never answered `cannot_be_determined` (0 of 150).

No report, rationale, or annotation text appears in this folder. Patients are TCGA IDs.

## Design

- **Patients:** the 50 annotated patients ([`inputs/roster.csv`](inputs/roster.csv)), scored against [`annotations/`](../../annotations/endo_myometrial_invasion/).
- **OncoTrace:** `fc3dadc` (main after dsi-rse/oncotrace#6), contract `ba27b6ce…`, GLM-5.3-Flash, agentic. This is a different contract from the #8 runs (`940b2a7b…`), so those runs are not baselines here.
- **One server start, four arms at once.** That's 2 workers each, 8 requests in flight. Running them together exposes every arm to the same server state.

| Arm | Config | Temperature / top_p | Runs |
|---|---|---|---|
| T0 | [`configs/t0.yaml`](configs/t0.yaml) | 0.0 / 1.0 | 1 |
| T1 | [`configs/t1.yaml`](configs/t1.yaml) | 1.0 / 0.95 | 3 repeats |

The two configs differ only in `temperature` and `top_p`. Apart from `roster:` and `artifacts:`, both are identical to [`config/endometrial.yaml`](../../config/endometrial.yaml).

## Layout

```text
compare_temperature.py   the one entry point: reads the runs, writes results/<timestamp>/
run_arms.sh              attaches all four arms to one running GLM server
configs/<arm>.yaml       OncoTrace run configs for the T0 and T1 arms
inputs/roster.csv        the 50 annotated patient IDs
results/<timestamp>/     one folder per analysis, with a README of its findings
```

Each results folder holds:

| File | What it holds |
|---|---|
| `per_run.csv` | One row per run: answered, invasion and depth agreement, `cannot_be_determined` count, calls (mean, median, max, patients with 8 or more), tokens, confidence split |
| `stability.csv` | Per setting with repeats: patients whose answer changed between repeats that both answered, and patients answered in only some repeats |
| `vs_baseline.csv` | Per setting: patients with more, fewer, or the same calls as T0, and the median per-patient token ratio |
| `patients.csv` | One row per run and patient: status, answer, annotation, agreement, confidence, calls, tokens |
| `summary.txt`, `provenance.json` | The printed numbers, and what the folder was made from |

The analysis reuses `src/oncotrace_bench/records.py` (load runs and annotations) and `provenance.py`.

### What is not in Git, and where it is

| What | Where |
|---|---|
| The four runs read by `compare_temperature.py` | `/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/2026-10-23_temperature_{t0,t1_r1,t1_r2,t1_r3}/` |

All four are readable by the `__oncotrace` group.

## Reproduce it

You need to be in the `__oncotrace` group (`id -nG` lists it) and have the clinic environment from [`docs/student-setup.md`](../../docs/student-setup.md). Run every command from the repo root.

### 1. Re-run the analysis on the existing runs (seconds, CPU)

```bash
make temperature
# or directly:
PYTHONPATH=src python experiments/temperature/compare_temperature.py
```

The CSV files in your new `results/<timestamp>/` should be byte-identical to the committed ones.

### 2. Re-run OncoTrace on the arms (about 4 h, 4 H200s)

1. Use an OncoTrace checkout at `fc3dadc` for an exact repeat. Check each config resolves: `unit_count` 50, contract `ba27b6ce…`.

   ```bash
   PYTHONPATH=~/oncotrace PYTHONNOUSERSITE=1 python -m oncotrace.runner check \
     --config experiments/temperature/configs/t1.yaml --output /tmp/$USER-none
   ```
2. Start a GLM-5.3-Flash server that stays up, as in OncoTrace's running guide. For example, submit `scripts/smoke_slurm_dsi.sbatch` with `ONCOTRACE_HOLD_SERVER=1` and your own `config/endometrial_local.yaml`, which holds the `serving:` block. Wait for its `endpoint.json`.
3. In tmux on the login node, attach the four arms:

   ```bash
   ONCOTRACE=~/oncotrace PY=~/envs/clinic-client/bin/python \
     experiments/temperature/run_arms.sh <server job id> <endpoint.json> <your runs folder>
   ```

   It makes a fresh folder per arm and runs all four, 2 workers each. When they finish, it cancels the server job, writes each run's table and review, and makes the folders group-readable.
4. Analyze them: `make temperature ARGS="--run t0=<run> --run t1_r1=<run> --run t1_r2=<run> --run t1_r3=<run>"`.

In the original run, the T0 arm was the serving job's own client and the three T1 arms attached to it. `run_arms.sh` attaches all four the same way, with the same 2 workers each.

At temperature 1.0, OncoTrace sends no seed, so a rerun will not repeat the same samples. Compare the counts, not the CSVs byte for byte.

## Caveats

- 50 patients, one annotator, not adjudicated, and 45 from one tissue source site. Only a large accuracy difference would show.
- One server start and a single T0 run. One answer change in 200 patient-runs is too few to say which setting is more stable.
- The four arms shared one server, so wall time per arm is not a clean cost measure. Use calls and tokens.
- Only 0.0 / 1.0 and 1.0 / 0.95 were tested. Other temperatures, or `top_p` changed on its own, are in #20.
