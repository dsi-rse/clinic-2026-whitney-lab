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
| `followup10.yaml`, `followup10_new_version.yaml` | The same config for 10 patients; the second is the one run with the new OncoTrace (`0b6f404`, 28 Oct). Only the comment lines differ. |
| `followup10_one_shot_new_version.yaml` | The same 10 patients in one_shot mode, new OncoTrace. Keep it in this folder: its task and roster paths are relative to it. |
| `roster_followup10.csv` | The 10 patients of the follow-up runs. |
| `run_repeats.sbatch`, `run_repeats.sh` | Slurm job: starts one server, then runs the same extraction `REPEATS` times. Every path comes from an environment variable. |
| `analyze_repeats.py` | Reads the repeats of one setting and writes the stability tables. |
| `repeat_matrix.py` | Puts two groups of repeats side by side: for each patient, which outcomes appeared and how often. |
| `run_analysis.sh` | One command that remakes every result folder below. |
| `results/<time>_agentic_f99cefd_50x5/` | 50 patients, 5 repeats, OncoTrace `f99cefd`. |
| `results/<time>_agentic_f99cefd_10x10/` | 10 patients, 10 repeats, OncoTrace `f99cefd`. |
| `results/<time>_agentic_0b6f404_10x20/` | The same 10 patients, 20 repeats, new OncoTrace `0b6f404` (28 Oct). |
| `results/<time>_one_shot_0b6f404_10x20/` | The same 10 patients, 20 repeats, new OncoTrace, one_shot mode. |
| `results/<time>_repeat_matrix_old_vs_new_10_patients/` | The two agentic 10-patient groups (old and new version) side by side. |
| `results/<time>_repeat_matrix_agentic_vs_one_shot_10_patients/` | The two new-version groups (agentic and one_shot) side by side. |

Each analysis folder has `report.md` (one page), the CSV tables, and `provenance.json`.
Only counts, patient IDs and OncoTrace reason codes are written, never report text.

## Results

OncoTrace versions: `f99cefd` is the code of 21 October 2026 (old version); `0b6f404` is the code of
28 October 2026 (new version, 10 commits later).

Model: GLM-5.3-Flash (`GLM-5.3-Flash-stripe8`), temperature 0.0; agentic mode unless a row says one_shot. All numbers
come from the tables in `results/`. Differences are descriptive; none was tested for
significance.

| Setting | OncoTrace | Patients | Repeats | Same outcome in every repeat | Where |
|---|---|---|---|---|---|
| 50 annotated patients | `f99cefd` | 50 | 5 | 49 of 50 | `..._50x5/report.md` |
| 10 patients | `f99cefd` | 10 | 10 | 9 of 10 | `..._10x10/report.md` |
| same 10 patients | `0b6f404` | 10 | 20 | 9 of 10 | `..._agentic_0b6f404_10x20/report.md` |
| same 10 patients, **one_shot** mode | `0b6f404` | 10 | 20 | 8 of 10 | `..._one_shot_0b6f404_10x20/report.md` |

An outcome is the invasion answer plus the depth answer, or "no answer". In the three agentic
settings every repeat answered every patient and the one unstable patient is `TCGA-A5-A0GR`.
In one_shot, 19 of 20 repeats answered every patient; in `rep19` one patient got no answer
(below).

**The one unstable patient** (`..._repeat_matrix_old_vs_new_10_patients/patient_stability.csv`).
The annotation for this patient is `present` with depth `less_than_50`.

| OncoTrace and mode | Repeats | `less_than_50` | `fifty_or_greater` | `cannot_be_determined` |
|---|---|---|---|---|
| `f99cefd`, agentic | 10 | 7 | 2 | 1 |
| `0b6f404`, agentic | 20 | 11 | 4 | 5 |
| `0b6f404`, one_shot | 20 | 17 | 0 | 3 |

The other 9 patients gave the same outcome in every repeat in both agentic runs. We do not
claim the updated version is more or less stable: this is one patient, 10 against 20
repeats. The agentic and one_shot counts for this patient are in
`..._repeat_matrix_agentic_vs_one_shot_10_patients/patient_stability.csv`.

**one_shot has its own unstable patient.** `TCGA-A5-A0R7` answered `present` with
`less_than_50` in 19 of 20 repeats and got no answer in 1 (`rep19`, where the patient used
all 24 model calls). In the agentic runs this patient never changed. The `rep19` run has 24
rejected submissions with the reason `argument_not_a_list` (the submitted list could not be
read as JSON); the same reason caused most of the no-answer cases in the full-cohort
baseline (issue 35). Every other one_shot patient had the same outcome in all 20 repeats.
So 8 of 10 patients are stable in one_shot (2 unstable) against 9 of 10 in agentic (1
unstable). With 10 patients this is not a difference we can call real.

**The route to the answer differs even when the answer does not.** Per patient, model calls
were identical across repeats for 6 of 50 patients (5 repeats), 0 of 10 (10 repeats) and 0
of 10 (20 repeats, agentic) and 0 of 10 (20 repeats, one_shot). Completion tokens were identical for 0 patients in all four.

**Cost per repeat** (`runs.csv` in each folder)

| Setting | Model calls per repeat | Completion tokens per repeat | Share of tokens in cut-off replies |
|---|---|---|---|
| 50 patients, 5 repeats | 206 to 266 | 363,849 to 565,024 | 16 to 38% |
| 10 patients, 10 repeats, `f99cefd` | 37 to 49 | 54,385 to 116,513 | 13 to 54% |
| 10 patients, 20 repeats, `0b6f404`, agentic | 37 to 51 | 66,843 to 128,029 | 12 to 69% |
| 10 patients, 20 repeats, `0b6f404`, one_shot | 16 to 42 | 46,723 to 83,132 | 13 to 55% |

A cut-off reply is one the server stopped at the reply token cap (8192; finish reason
`length`). In the 5-repeat run, rep1 had the most (26 replies, 21 patients) and the highest
cost; why is not known (chance, or the first server start; the run was split over two
server starts, so the two cannot be separated).

**Agreement with the annotations** (`annotation_agreement.csv`; a single-annotator
development reference; no answer counts as not agreeing). Invasion: 47 of 50 in every
5-repeat run, and 10 of 10 in every repeat of the agentic 10-patient runs. In one_shot,
invasion is 10 of 10 in 19 of 20 repeats and 9 of 10 in `rep19` (the no-answer patient).
Depth, 10 patients: 8 or 9 of 10 per repeat in all three. In the agentic runs the misses are
the repeats where `TCGA-A5-A0GR` did not answer `less_than_50` (3 of 10 repeats with
`f99cefd`, 9 of 20 with `0b6f404`). In one_shot, 16 repeats had 9 of 10 and 4 had 8 of 10.

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

`<prefix>` is any name for this rerun, such as `2026-11-03_120000`. The rerun makes all six result folders and takes about 1 to 2 minutes (measured: 76 seconds in a fresh clone; the first read of the shared disk can be slower). Python 3.12 with
`httpx`, `pyyaml` and `pydantic` is needed, because the analysis imports TraceView's
`viewer/scoring.py` from the OncoTrace checkout (only that file is read; use clean checkouts,
because the provenance check fails on a checkout with uncommitted or untracked files); set `PYTHON` to
that interpreter if `python3` is not it. The tables reproduce byte for byte;
`provenance.json` and the first line of `report.md` differ only in the time, the commit,
the folder name and the relative path to the OncoTrace checkout.

Run folders used: `2026-10-25_determinism_5x`, `2026-10-28_followup_10x10`,
`2026-10-30_followup_10x20_main0b6f404`, `2026-11-02_followup_10x20_one_shot_main0b6f404`.

## Provenance and what cannot be rerun

`provenance.json` is made with `oncotrace_bench.provenance.build` (issue 31 format) and passes
`make check-provenance ARGS=experiments/endometrial_determinism` (0 problems; it prints "not checked" notes, explained below). It records the clinic commit,
the config and roster SHA-256, the OncoTrace commit and task digest each run record names,
the Slurm jobs (state, time, node, records written), the config digest and serving image
fingerprint from the job logs, and checkpoint, seed and caching from the server log.

- **The runs themselves cannot be rerun to the same records.** Repeats are not identical;
  that is what this experiment measures.
- **Resumed runs.** 5 repeats: two jobs (`2239457` timed out during repeat 2, `2244400`
  finished it). 10 repeats, `f99cefd`: two jobs (`2260881`, `2267023`). 20 repeats,
  `0b6f404`: four jobs, each with its own server start (`2284447` and `2286351` timed out,
  `2287510` failed after 39 minutes when the vLLM engine died, `2287759` finished).
  So the repeats do not all share one server. one_shot, 20 repeats, `0b6f404`: three
  jobs (`2297402` and `2297952` timed out after the 2-hour limit, `2298797` finished); the
  job logs are in the run folder's `job_logs`.
- **Server logs.** Only the last server start of each run has a log; earlier ones were
  overwritten when the next job started.
- **Job script.** The first three tests were started with the earlier version of
  `run_repeats.sbatch`, which had personal paths as defaults. The one_shot run used the
  version in this folder, which only removes those defaults; it ran in three jobs without
  change. The one_shot jobs ran in the `protected` queue (2-hour limit, one job at a time).
  A small loop script, not committed, submitted the next job when the last one ended;
  it ran the same `sbatch` command as above.
- **"Not checked" notes in the provenance check.** For the one_shot run and the
  agentic-vs-one_shot table, the check prints one "no job log in the run folder" note per
  repeat. It looks for `job-*.out` inside each repeat folder, and ours are in `job_logs`
  one level up, so it cannot say how many server starts served each repeat. The jobs are
  recorded in `slurm_jobs` and `logged_by_jobs` in the same `provenance.json`. It also
  prints "not checked" for commits on GitHub because the checker had no GitHub access
  here; we checked by hand that the clinic commit is on GitHub.
- **Dependencies on unmerged PRs.** None. `provenance.build` and `scripts/check_provenance.py`
  come from PR #38 (issue 31), which is merged. Step-by-step trace cards of the unstable
  patient were made with `trace_cards.py` from the unmerged issue 16 PR; they were removed
  from this PR for that reason.

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
