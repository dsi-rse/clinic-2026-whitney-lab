# Endometrial failure modes

**Question.** When OncoTrace reads endometrial pathology reports, why does it
sometimes give no accepted answer, can we spot unreliable answers, and does its
own confidence rating help?

**Why it matters.** A missing answer is a lost patient, and a confident wrong
answer is worse. We want to know which failures come from the model, which from
OncoTrace's own checks, and which a fix to OncoTrace could remove. This experiment
is the measuring stick: run it on a run made with today's OncoTrace, then run it
again on a run made with a fix, and compare.

## What it does

Reads one OncoTrace run through TraceView and writes a folder of tables:

| File | What it counts |
|---|---|
| `outcome.csv` | Roster patients as accepted answer, no accepted submission, server error, unfinished |
| `invasion.csv`, `depth.csv` | Accepted answers by value, including `cannot_be_determined` (an indeterminate clinical answer is an accepted answer) |
| `confidence.csv` | Agreement with the human annotations, by the model's confidence (high, medium, low, none) |
| `refusals.csv` | What the model was refused on, how many patients, and how many still answered |
| `patients.md` | A text-free trajectory (steps, read ranges, refusals, truncation) for chosen patients |
| `report.md` | All of the above on one page |
| `provenance.json` | What it was made from: inputs, counts, OncoTrace and clinic-repo commits and uncommitted files |

No report text is written anywhere; only counts, IDs and character offsets.

## Run it

You need the clinic environment (`pip install -e .` from the repo root), an
OncoTrace clone (for TraceView), and a run folder.

```bash
make endometrial-failure-modes RUN=/path/to/run LABEL=baseline
# or directly:
PYTHONPATH=src python experiments/endometrial_failure_modes/run_experiment.py \
  --run /path/to/run --label baseline
```

Results go to `results/<LABEL>/`. A label that already exists is refused, so earlier
results are never overwritten. Useful options: `--oncotrace` (the OncoTrace clone,
default `~/oncotrace`), `--units` (patients for `patients.md`), `--task`, `--roster`,
`--annotations`, `--project`.

## Re-run it later

**After an OncoTrace fix.** Make a new run with the fixed OncoTrace (see OncoTrace's
running guide), keeping the same task contract, roster and annotations. Run the
experiment on it with a new label, e.g. `LABEL=after-pr7`, and point `--oncotrace`
at the clone you are testing. Compare its folder with `results/baseline/`: look at whether `no accepted submission`
falls, whether the refusals the fix targets shrink, and whether `confidence.csv`
shows new disagreements. What counts as an improvement is for you and your mentor to
agree before the second run. `provenance.json` records the OncoTrace
commit (and any uncommitted files) so each result names the code that made it.

**With more annotations.** Add annotation files under `annotations/`, then run again
with a new label. `confidence.csv` then covers more patients; compare only results
made on the same run and the same annotation count, which `provenance.json` records
(`annotations_matched`).

**On a run that is still in progress.** Counts change as records arrive. Use a new
label and read `run_records` in `provenance.json`.

## Layout

```text
run_experiment.py   the one entry point
failure_tables.py   the tables this experiment reports
provenance.py       what each result folder was made from
findings/           what the first run showed, and what to test next
results/<label>/    one folder per run of the experiment
```

General helpers other analyses can reuse (loading a run through TraceView, reading
a roster, classifying outcomes, summarizing a patient's trajectory) live in
`src/oncotrace_bench/traceview_summary.py`.

## Findings so far

From the baseline (OncoTrace run `endometrial_glm53_20261012`, 498 of 546 records):

- 44 patients ended with no accepted submission: 32 used all 24 calls on refused
  quotes and 12 had replies cut off at the 8192-token cap three times.
- The model's confidence does not separate good from bad answers: 46 of 47 scored
  answers are `high`, and both disagreements with the annotations are `high`.
- Details: [patient inspections](findings/patient-inspections.md),
  [confidence and agreement](findings/confidence-agreement.md), and a
  [proposed test of the truncation explanation](findings/failure-test-proposal.md).

Fixes under test live in the OncoTrace repo: PR #7 (what the model is told when a
quote is refused or a reply is cut off) and PR #9 (TraceView filters for refusals
and cut-off replies).

## Caveats

- The annotations (50 patients, 45 from one site) are a development reference, not
  an independent test set. TraceView scores all 50 as "prospective" only because the
  annotation project declares no development units.
- The run was in progress when the baseline was made.
- The experiment reads the OncoTrace clone's TraceView code. Check
  `provenance.json` for uncommitted files in that clone before comparing results.
