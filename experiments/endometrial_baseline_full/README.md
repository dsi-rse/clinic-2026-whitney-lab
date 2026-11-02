# Full-cohort baseline of the updated OncoTrace (issue 35)

Runs OncoTrace (main at `0b6f404`, 2026-10-28) on all 546 TCGA-UCEC patients and
reports how often it gives an answer and what that costs. There are no manual
annotations for most patients, so this experiment does not measure whether the
labels are right. The numbers are in `results/<date_time>_<label>/` (written by
`run_analysis.py`, with its own `README.md` that explains each table).

## What is here

| File | What it is |
|---|---|
| `full_agentic.yaml`, `full_one_shot.yaml` | Run configs. They differ only in `mode` and the `one_shot` block. |
| `run_extraction.sbatch`, `run_extraction.sh` | Slurm job and driver: serve the model, then extract. |
| `keep_one_protected_job.sh` | Resubmits the job (2 h `protected` queue) until all patients have a record. |
| `roster_annotated50.csv` | The 50 patients with manual annotations (single annotator). |
| `summarize_runs.py` | Completion and cost of any runs, side by side. |
| `compare_modes.py` | Agentic against one_shot: outcomes, differences, agreement with annotations. |
| `case_across_runs.py` | What every run did on chosen patients. |
| `case_steps.py` | Step by step, what each run did on those patients (codes and counts only). |
| `run_analysis.py` | Runs the four scripts above, writes `provenance.json` and a results README. |

## Rerun the analysis from a fresh clone
You need Python 3.11 or later (standard library only) and read access to the run
folders below (group `__oncotrace`).

```bash
git clone https://github.com/dsi-rse/clinic-2026-whitney-lab.git
cd clinic-2026-whitney-lab
git checkout <this branch or main after merge>
RUNS=/net/spaces/annawoodard/oncotrace/workspaces/yuxuang/runs
PYTHONPATH=src python experiments/endometrial_baseline_full/run_analysis.py \
  --agentic $RUNS/2026-10-29_baseline_full_main0b6f404/rep1 \
  --one-shot $RUNS/2026-10-30_one_shot_full_main0b6f404/rep1 \
  --issue9-agentic $RUNS/2026-10-12_endometrial_agentic \
  --issue9-one-shot $RUNS/2026-10-16_endometrial_one_shot \
  --issue17-runs $RUNS/2026-10-25_determinism_5x \
  --annotations annotations/endo_myometrial_invasion \
  --label rerun
```
It writes a new folder `results/<date_time>_rerun/` and never overwrites another.

- **Reproduces exactly:** every CSV in the new folder equals the committed one in
  `results/`. `provenance.json` differs only in `created_utc`.
- **Time:** a few seconds when the run files are in the disk cache (6 s measured); the first read of the shared disk can take several minutes.

## Rerun the extraction (does not reproduce bit for bit)
GPU runs cannot be repeated exactly: even at temperature 0, answers can differ
between identical runs (see issue 17). The run folders below are kept, and the
analysis above reads them.

```bash
export ONCOTRACE_REPO=/path/to/oncotrace            # checkout at 0b6f404
export ONCOTRACE_PYTHON=/path/to/client/bin/python  # needs pyyaml, pydantic, httpx
export EXCLUDE=r001,r002,o001                       # nodes we avoided (optional)
experiments/endometrial_baseline_full/keep_one_protected_job.sh OUTPUT_FOLDER 546
# one_shot: CONFIG=experiments/endometrial_baseline_full/full_one_shot.yaml
```
The `serving:` block of the configs holds cluster paths (serving environment,
model weights, caches, and `rpc_base_path`, which must be short). They are copied
unchanged from the runs; replace them with your own before submitting.
Our serving image was `ONCOTRACE_SERVING_IMAGE=/net/spaces/scratch/yuxuang-oncotrace/envs/vllm-glm53.sqfs`.

## Inputs that are not in this repository
Protected report text; do not copy it anywhere public.
- Where: `/net/spaces/annawoodard/oncotrace/data/endometrial/` (readable by group `__oncotrace`).
- `roster_ucec.csv` SHA-256 `6e42b571ce6e9f1998acffa426d13f4b0fece34415a2675f8f0e7dd7fe7774b6`
- `documents/ucec_pathology_report.jsonl` SHA-256 `d0f547d43adc8076e11a821244734c8adb3f4fc0570c0d6d884821b0a220087f`
- That folder has its own `README.md`, `manifest.json` and `SHA256SUMS`, with the
  commands that recreate the files from the original source.
- Task contract: `tasks/endo_myometrial_invasion.yaml` in this repo.

## The runs, and how they were made
All under `/net/spaces/annawoodard/oncotrace/workspaces/yuxuang/runs/`. Each run
was resumed after time-outs: a resubmitted job skips patients that already have a
record, so one run was made by several jobs (and servers).

| Run folder | OncoTrace | Slurm jobs |
|---|---|---|
| `2026-10-29_baseline_full_main0b6f404` (agentic) | `0b6f404` | 2270807 (general, 12 h, TIMEOUT); 2274402, 2275116, 2275887, 2276790 (protected, TIMEOUT); 2277625 (COMPLETED) |
| `2026-10-30_one_shot_full_main0b6f404` (one_shot) | `0b6f404` | 2278119 (FAILED: vLLM CUDA error on r002 after 64 records); 2279012, 2279890, 2280403, 2281307, 2281662 (TIMEOUT); 2282129 (COMPLETED) |
| `2026-10-12_endometrial_agentic`, `2026-10-16_endometrial_one_shot` | `e901b3f` | Issue 9 runs, older code |
| `2026-10-25_determinism_5x` (rep1 to rep5) | `f99cefd` | Issue 17 runs, 50 annotated patients |

`job_logs/` in each run folder holds the job outputs.

## What this does not show
- Single run per mode; one_shot's own run-to-run variation is not measured.
- One document per patient (a short pathology report), so one_shot may not hold
  for longer records.
- Different OncoTrace versions are compared descriptively; the cause of a
  difference cannot be assigned to one change.
- The task contract digest of the one_shot run (`ca152404…`) differs from the
  agentic run (`ba27b6ce…`); the reason has not been checked.
- Only 50 patients have annotations, from one annotator.
