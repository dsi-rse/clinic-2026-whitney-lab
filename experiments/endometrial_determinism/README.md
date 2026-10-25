# Endometrial: are repeated OncoTrace runs the same? (issue 17)

**Question.** With the same model, code, configuration and patients, does OncoTrace give
the same answers every time? If not, how much does it vary and where does the
difference start?

**Why it matters.** Differences between two settings (issue 16) only mean something if
we know how much two identical runs already differ. The agentic vs one_shot gap in
`endometrial_agentic_vs_one_shot` (37 vs 34 of 50 on depth) is only three patients wide.

## Files

| File | What it is |
|---|---|
| `default.yaml` | The agentic config used for issue 9, with the roster narrowed to the 50 annotated patients. Everything else is identical, and `runner check` gives the same task contract digest. |
| `roster_annotated50.csv` | The 50 annotated patients, one `unit` per row. Swap this file to run on more patients later. |
| `run_repeats.sbatch` | Slurm job: starts one server, then runs the same extraction `REPEATS` times (default 5). |
| `run_repeats.sh` | What the job runs inside the allocation. Each repeat writes to its own folder, `rep1` ... `repN`. |
| `analyze_repeats.py` | Reads two or more runs and writes the stability tables under `results/<label>/`. |

## Run it

Submit from any directory. The output folder must be new, because a folder that already
holds records is resumed, not rerun.

```bash
sbatch --exclude=r002,o001 --time=08:00:00 --cpus-per-task=32 \
  --export=ALL,ONCOTRACE_OUTPUT=/path/to/new/run_folder \
  experiments/endometrial_determinism/run_repeats.sbatch
```

Then analyse, with a label that has not been used:

```bash
python experiments/endometrial_determinism/analyze_repeats.py \
  --reps-dir /path/to/new/run_folder --label default_5x
```

`results/<label>/` gets `report.md` (everything on one page), `runs.csv`, `per_patient.csv`,
`unstable_patients.csv`, `spread.csv`, `divergence.csv`, `pairwise_agreement.csv`,
`refusals.csv`, `annotation_agreement.csv` and `provenance.json`. Only counts, patient IDs
and OncoTrace reason codes are written, never report text. Use `--runs A B ...` to compare
any runs instead of `rep*` folders.

## What the tables measure

- **Unstable patients:** patients whose outcome (invasion and depth, or no answer) is not
  the same in every run. `unstable_patients.csv` says whether the label changed or the
  patient was only answered in some runs.
- **Spread:** for the same patient, how much calls, completion tokens and rejected
  submissions differ between runs.
- **Where the runs first differ:** whether the first reply, and the first long reasoning
  reply, are identical across runs.

## Results (5 repeats, 50 annotated patients, OncoTrace `f99cefd`, GLM-5.3-Flash)

Tables: `results/default_5x_cpu32/`. The run was split over two server starts (the first Slurm
job hit its time limit during repeat 2 and a second job resumed it), so the repeats did not all
share one server.

- **The final answer is nearly repeatable.** 49 of 50 patients had the same invasion and depth
  answer in all 5 runs; all 250 patient-runs were answered. One patient (`TCGA-A5-A0GR`) got a
  different depth in one run.
- **The route to the answer is not.** Model calls were identical across the 5 runs for 6 of
  50 patients, completion tokens for 0 of 50, and the first long reasoning reply for 0 of 50.
  Per run, calls ranged 206 to 266 and completion tokens 364k to 565k.
- **Cut-off replies drive most of the cost spread.** Replies cut off at the 8192-token cap:
  26 in rep1 (21 patients) against 7 to 14 in the other runs. They hold 16 to 38% of the tokens.
  Why rep1 had more is not known (chance, or the first server start; the split run cannot
  separate them).
- **Agreement with the annotations** (a single-annotator development reference, 50 patients):
  invasion 47 of 50 in every run; depth 38 of 50 in four runs and 37 of 50 in one. Most of
  the rest are answers given where the annotation is `not_applicable` or
  `cannot_be_determined`; this is not read as model error.
- **Not tested yet:** the controls below, so the source of the variation is not identified.

## Known pitfalls

- **Keep 32 CPUs.** With 16 the server generated 25 to 50 tokens/s, against about 127 with 32
  (roughly 3 to 5 times slower; measured once; the four model workers use about 3 cores each),
  and could not finish in the time limit.
- **One repeat takes about 1 to 1.5 hours,** so five repeats need 5 to 7 hours. Set
  `--time=08:00:00`, not 2 hours; a job that times out is resumed by submitting again to the
  same output folder.
- **Pin the code version.** The job reads OncoTrace from `~/oncotrace` when it starts, so
  do not change that checkout while a job is queued. Record the commit; the analysis writes
  it to `provenance.json`. The issue 9 runs used `e901b3f`.
- **Repeats on one server measure stability within that server**, not across server
  starts. Run a second job to compare server starts.

## Still to do for issue 17

Candidate sources, from the serving config: requests batched together (3 client workers,
`max_num_seqs` 8), speculative decoding (MTP, 5 tokens), prefix caching and chunked
prefill, and retry loops that amplify a small difference. Controls to compare against the
default: one client at a time, MTP off, prefix caching off, and a second fresh server
start. The per-request seed is not sent by the client and the server seed is already 0, so
it is unlikely to matter at temperature 0.
