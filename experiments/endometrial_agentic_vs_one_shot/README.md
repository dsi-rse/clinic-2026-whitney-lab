# Endometrial: agentic vs one_shot

**Question.** OncoTrace can read a pathology report two ways. In `agentic` mode the
model searches and reads the report in pieces, then submits an answer with quoted
evidence. In `one_shot` mode the whole report is in the prompt and the model submits
once (it can still be refused and retry). Does the extra machinery of `agentic` mode
buy more answered patients, more agreement with the human annotations, or fewer
failures, and what does it cost?

**Why it matters.** `agentic` mode makes about 1.6 times as many model calls
(2,790 vs 1,711 on the baseline), so it is only worth keeping if it answers more
patients or answers them better. It also decides where to spend effort fixing
OncoTrace: if both modes lose patients for the same reason, the fix belongs in
OncoTrace's checks and limits, not in the choice of mode.

## What it does

`run_comparison.py` reads one `agentic` run and one `one_shot` run through TraceView,
pairs them by patient, and writes a labelled folder under `results/`. Every table is
over the patients **both** runs have a record for, so a run that finished more
patients is not flattered.

| File | What it counts |
|---|---|
| `outcome.csv` | Patients answered by both, only one, or neither mode |
| `not_answered.csv` | Why a patient got no answer, by OncoTrace's own reason code |
| `totals.csv` | Model calls, prompt and completion tokens (the server's counts), refusals |
| `refusals.csv` | What each mode was refused on, and for how many patients |
| `agreement_invasion.csv`, `agreement_depth.csv` | Agreement with the annotations: correct, wrong, over-committed, abstained, coverage, accuracy, and an exact McNemar p-value on the patients where the modes differ |
| `disagreements.csv` | Patient IDs where one mode answered and the other did not, or the values differ (the list to open in TraceView) |
| `report.md` | All of the above on one page |
| `provenance.json` | What the result was made from: run folders, each run's own provenance (code commit, config hash, model, temperature), task hash, OncoTrace and clinic-repo commits |

No report text is written anywhere: only counts, patient IDs and reason codes.
Accuracy charges an unanswered patient as wrong; `accuracy_if_answered` and `coverage`
are shown beside it because either alone misleads. "Always the commonest annotation"
is shown as a baseline so a score can be read against doing nothing clever.

## The two arms

| | agentic | one_shot |
|---|---|---|
| Config | [`config/endometrial.yaml`](../../config/endometrial.yaml) | [`one_shot.yaml`](one_shot.yaml) |
| Difference | | `mode: one_shot` and `one_shot.max_source_chars: 120000`, nothing else |

The longest report on the roster is 17,875 characters, so `max_source_chars` excludes
no patient. Same model, temperature, limits (24 calls, 8,192 completion tokens) and
roster (546 patients) in both arms.

## Run it

You need the clinic environment, an OncoTrace clone **that has `records.pair()`** in
`viewer/records.py` (OncoTrace pull request #8; until it is merged, check out branch
`yuxuang/paired-compare`), and two finished runs. Make the runs following
[OncoTrace's running guide](https://github.com/uchicago-dsi/oncotrace/blob/main/docs/running.md),
one per config, each with its own output folder, then:

```bash
python experiments/endometrial_agentic_vs_one_shot/run_comparison.py \
  --agentic /path/to/agentic_run --one-shot /path/to/one_shot_run \
  --label baseline
```

Results go to `results/<label>/`. A label that already exists is refused, so earlier
results are never overwritten. Options: `--oncotrace` (default `~/oncotrace`),
`--task`, `--annotations` (default `annotations/`), `--project`. It needs the
OncoTrace client environment (PyYAML and the packages TraceView imports).

## Re-run it later

**After an OncoTrace fix.** Make two new runs with the fixed OncoTrace, keeping the
task contract, roster, configs and annotations, and run the script with a new label
(for example `LABEL=after-fix`). Compare its folder with `results/baseline/`. Look at
whether the reasons in `not_answered.csv` that the fix targets shrink, whether the
refusal counts fall, and whether agreement holds. What counts as an improvement is
for you and your mentor to agree **before** the second run. `provenance.json` names
the OncoTrace commit that made each result.

**With more annotations.** Add files under `annotations/endo_myometrial_invasion/` and
run again with a new label. Compare only results with the same `scored` counts in
`provenance.json`.

**On a run still in progress.** Counts change as records arrive; use a new label and
read the record counts in `provenance.json`.

## Baseline (`results/baseline/`)

Made on 2026-10-19 from two complete 546-patient runs (GLM-5.3-Flash, OncoTrace
`e901b3f`). The agentic run used a personal copy of `config/endometrial.yaml` with an
added `serving` block (how the server was started), and no other change. The runs
themselves hold protected report text and stay outside Git, under
`/net/spaces/annawoodard/oncotrace/workspaces/yuxuang/runs/`.

| | agentic | one_shot |
|---|---|---|
| Answered (of 546) | 503 | 496 |
| No answer: calls used up | 26 | 19 |
| No answer: reply cut off at 8,192 tokens | 17 | 31 |
| Model calls | 2,790 | 1,711 |
| Prompt / completion tokens | 18.7M / 4.8M | 13.7M / 5.9M |
| Invasion agrees with annotation (of 50) | 46 | 43 |
| Depth agrees with annotation (of 50) | 37 | 34 |

What this says, and what it does not:

- Neither mode answers every patient, and they fail differently. `agentic` mostly runs
  out of calls; `one_shot` mostly has its reply cut off. So what: a patient with no
  answer is a lost patient, and the cut-off replies point at a token limit that a fix
  could change, not at hard cases.
- 466 patients are answered by both, with the same invasion value for every one and a
  different depth value for two. 37 patients are answered only by `agentic` and 30 only
  by `one_shot`: the two modes lose largely **different** patients.
- Against the 50 annotations, `agentic` is ahead by 3 patients on both questions, but
  only 4 vs 1 patients separate them (exact McNemar p = 0.375). So what: this does not
  show that either mode is better. It is also close to "always say present" for
  invasion (45/50).
- The 50 annotations are a development reference from medical students, 45 from one
  tissue source site, not an independently adjudicated test set.
- Three patients worth opening in TraceView, read by hand on 2026-10-18 (re-check them):
  `TCGA-A5-A0R7` (one_shot: a quote differed from the report by one character, then
  two replies hit the cap), `TCGA-A5-A0GR` (one_shot: three replies in a row hit the
  cap) and `TCGA-A5-A0VQ` (agentic: the same ambiguous quote submitted until the
  24 calls ran out).

## Layout

```text
run_comparison.py   the one entry point
one_shot.yaml       the one_shot arm's config
results/<label>/    one folder per run of the experiment
```
