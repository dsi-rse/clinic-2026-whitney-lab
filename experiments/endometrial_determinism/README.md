# Endometrial: are repeated OncoTrace runs the same? (issue 17)

**Question.** With the same model, code, configuration and patients, does OncoTrace give
the same answers every time? If not, how much does it vary?

**Why it matters.** Differences between two settings (issue 16) only mean something if
we know how much two identical runs already differ.

## What is in this folder

| File | What it is |
|---|---|
| `default.yaml` | Agentic config of issue 9, roster narrowed to the 50 annotated patients. |
| `roster_annotated50.csv` | The 50 annotated patients (column `unit`). |
| `followup10.yaml`, `followup10_new_version.yaml` | The same config for 10 patients; the second is the one run with the updated OncoTrace (`0b6f404`). Only the comment lines differ. |
| `roster_followup10.csv` | The 10 patients of the follow-up runs. |
| `run_repeats.sbatch`, `run_repeats.sh` | Slurm job: starts one server, then runs the same extraction `REPEATS` times. Every path comes from an environment variable. |
| `analyze_repeats.py` | Reads the repeats of one setting and writes the stability tables. |
| `repeat_matrix.py` | Puts two groups of repeats side by side: for each patient, which outcomes appeared and how often. |
| `run_analysis.sh` | One command that remakes every result folder below. |
| `results/<time>_agentic_f99cefd_50x5/` | 50 patients, 5 repeats, OncoTrace `f99cefd`. |
| `results/<time>_agentic_f99cefd_10x10/` | 10 patients, 10 repeats, OncoTrace `f99cefd`. |
| `results/<time>_agentic_0b6f404_10x20/` | The same 10 patients, 20 repeats, updated OncoTrace `0b6f404`. |
| `results/<time>_repeat_matrix_old_vs_new_10_patients/` | The last two groups side by side. |
| `results/unstable_A0GR_rep1` to `rep5` | Step-by-step trace cards of the one unstable patient in the 5-repeat run (no report text). They were made with `trace_cards.py` from the issue 16 PR, which is not merged. |

Each analysis folder has `report.md` (one page), the CSV tables, and `provenance.json`.
Only counts, patient IDs and OncoTrace reason codes are written, never report text.

## Results

Model: GLM-5.3-Flash (`GLM-5.3-Flash-stripe8`), agentic mode, temperature 0.0. All numbers
come from the tables in `results/`. Differences are descriptive; none was tested for
significance.

| Setting | OncoTrace | Patients | Repeats | Same outcome in every repeat | Where |
|---|---|---|---|---|---|
| 50 annotated patients | `f99cefd` | 50 | 5 | 49 of 50 | `..._50x5/report.md` |
| 10 patients | `f99cefd` | 10 | 10 | 9 of 10 | `..._10x10/report.md` |
| same 10 patients | `0b6f404` | 10 | 20 | 9 of 10 | `..._10x20/report.md` |

An outcome is the invasion answer plus the depth answer, or "no answer". Every repeat
answered every patient. In all three settings the one unstable patient is `TCGA-A5-A0GR`.

**The one unstable patient** (`..._repeat_matrix_old_vs_new_10_patients/patient_stability.csv`).
The annotation for this patient is `present` with depth `less_than_50`.

| OncoTrace | Repeats | `less_than_50` | `fifty_or_greater` | `cannot_be_determined` |
|---|---|---|---|---|
| `f99cefd` | 10 | 7 | 2 | 1 |
| `0b6f404` | 20 | 11 | 4 | 5 |

The other 9 patients gave the same outcome in every repeat, in both versions. We do not
claim the updated version is more or less stable: this is one patient, 10 against 20
repeats.

**The route to the answer differs even when the answer does not.** Per patient, model calls
were identical across repeats for 6 of 50 patients (5 repeats), 0 of 10 (10 repeats) and 0
of 10 (20 repeats). Completion tokens were identical for 0 patients in all three.

**Cost per repeat** (`runs.csv` in each folder)

| Setting | Model calls per repeat | Completion tokens per repeat | Share of tokens in cut-off replies |
|---|---|---|---|
| 50 patients, 5 repeats | 206 to 266 | 363,849 to 565,024 | 16 to 38% |
| 10 patients, 10 repeats, `f99cefd` | 37 to 49 | 54,385 to 116,513 | 13 to 54% |
| 10 patients, 20 repeats, `0b6f404` | 37 to 51 | 66,843 to 128,029 | 12 to 69% |

A cut-off reply is one the server stopped at the reply token cap (8192; finish reason
`length`). In the 5-repeat run, rep1 had the most (26 replies, 21 patients) and the highest
cost; why is not known (chance, or the first server start; the run was split over two
server starts, so the two cannot be separated).

**Agreement with the annotations** (`annotation_agreement.csv`; a single-annotator
development reference). Invasion: 47 of 50 in every 5-repeat run, and 10 of 10 in every
repeat of the 10-patient runs. Depth, 10 patients: 8 or 9 of 10 per repeat in both
versions; the misses are the repeats where `TCGA-A5-A0GR` did not answer `less_than_50`
(3 of 10 repeats with `f99cefd`, 9 of 20 with `0b6f404`).

## Run it

Needs a new, empty output folder (a folder that already holds records is resumed, not
rerun), a clone of OncoTrace, and its client Python. Nothing is assumed about your home.

```bash
ONCOTRACE_REPO=/path/to/oncotrace ONCOTRACE_PYTHON=/path/to/client/bin/python \
ONCOTRACE_CONFIG=$PWD/experiments/endometrial_determinism/default.yaml \
ONCOTRACE_OUTPUT=/path/to/new/run_folder \
DETERMINISM_DRIVER=$PWD/experiments/endometrial_determinism/run_repeats.sh REPEATS=5 \
  sbatch --exclude=r001,r002,o001 --time=08:00:00 --cpus-per-task=32 \
  --output=/path/to/new/run_folder/job_logs/job-%j.out \
  experiments/endometrial_determinism/run_repeats.sbatch
```

`ONCOTRACE_SERVING_IMAGE` (a squashfs of the serving environment) is optional. The config
files still contain cluster paths for the model weights, serving environment, caches and
`rpc_base_path`; edit them for another account.

## Rerun the tables

The runs (records, job logs, the server log of the last server start) are in the shared
workspace, readable by the `__oncotrace` group. They contain protected report text, so
they stay there and are not committed.

```bash
git clone https://github.com/dsi-rse/clinic-2026-whitney-lab.git && cd clinic-2026-whitney-lab
git checkout yuxuang/issue17-determinism
RUNS=/net/spaces/annawoodard/oncotrace/workspaces/yuxuang/runs \
ONCOTRACE_F99CEFD=/path/to/oncotrace_at_f99cefd ONCOTRACE_0B6F404=/path/to/oncotrace_at_0b6f404 \
PYTHONPATH=src bash experiments/endometrial_determinism/run_analysis.sh <prefix>
```

`<prefix>` is any name for this rerun, such as `2026-11-03_120000`. Python 3.12 with
`httpx`, `pyyaml` and `pydantic` is needed, because the analysis imports TraceView's
`viewer/scoring.py` from the OncoTrace checkout (only that file is read; use clean checkouts,
because the provenance check fails on a checkout with uncommitted or untracked files); set `PYTHON` to
that interpreter if `python3` is not it. The tables reproduce byte for byte;
`provenance.json` and the first line of `report.md` differ only in the time, the commit and
the folder name.

Run folders used: `2026-10-25_determinism_5x`, `2026-10-28_followup_10x10`,
`2026-10-30_followup_10x20_main0b6f404`.

## Provenance and what cannot be rerun

`provenance.json` is made with `oncotrace_bench.provenance.build` (issue 31 format) and passes
`make check-provenance ARGS="experiments/endometrial_determinism --no-github"`. It records the clinic commit,
the config and roster SHA-256, the OncoTrace commit and task digest each run record names,
the Slurm jobs (state, time, node, records written), the config digest and serving image
fingerprint from the job logs, and checkpoint, seed and caching from the server log.

- **The runs themselves cannot be rerun to the same records.** Repeats are not identical;
  that is what this experiment measures.
- **Resumed runs.** 5 repeats: two jobs (`2239457` timed out during repeat 2, `2244400`
  finished it). 10 repeats, `f99cefd`: two jobs (`2260881`, `2267023`). 20 repeats,
  `0b6f404`: four jobs, each with its own server start (`2284447` and `2286351` timed out,
  `2287510` failed after 39 minutes when the vLLM engine died, `2287759` finished).
  So the repeats do not all share one server.
- **Server logs.** Only the last server start of each run has a log; earlier ones were
  overwritten when the next job started.
- **Job script.** The runs were started with the earlier version of `run_repeats.sbatch`,
  which had personal paths as defaults. The version here only removes those defaults; it
  has not been submitted as a job.
- **Dependencies on unmerged PRs.** `provenance.build` and `scripts/check_provenance.py` come
  from PR #38 (issue 31), which this branch has merged in; until #38 is merged into main,
  this PR's diff also shows #38's files. `trace_cards.py` (issue 16 PR) made the trace cards.

## Known pitfalls

- **Keep 32 CPUs.** With 16 the server generated 25 to 50 tokens/s, against about 127 with
  32, and could not finish in the time limit (measured once).
- **One repeat of 50 patients takes about 1 to 1.5 hours,** so five repeats need 5 to 7
  hours. Set `--time=08:00:00`. A job that times out is resumed by submitting again to the
  same output folder.
- **Pin the code version.** The job reads OncoTrace from `ONCOTRACE_REPO` when it starts,
  so do not change that checkout while a job is queued.
- **Repeats on one server measure stability within that server**, not across server starts.

## Still to do for issue 17

The controls the issue asks for: one client at a time, speculative decoding (MTP) off,
prefix caching off, and a second fresh server start. Until then the source of the
variation is not identified. The per-request seed is not sent by the client and the server
seed is already 0.
