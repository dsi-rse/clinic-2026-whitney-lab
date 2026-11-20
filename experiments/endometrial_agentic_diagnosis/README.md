# Endometrial: what makes agentic extraction fail, and which setting helps (issue 16)

**Question.** Issue 9 showed that agentic extraction leaves patients without an answer for
two reasons: the model's reply is cut off at the token cap, or it resends the same reply
after the same rejected submission until the call limit runs out. Which setting changes
reduce those failures, and what do they cost in accuracy and effort?

**Method.** One setting is changed per arm, always against the same baseline, on the same
50 annotated patients, with the same model and the same OncoTrace commit. Nothing else moves.

| Arm | Setting changed from the baseline | Compares |
|---|---|---|
| baseline | none: the default config of the issue 17 repeats | |
| `calls6`, `calls12` | `limits.model_calls` 24 to 6 or 12 | call budget (3 levels with the baseline) |
| `compact` | `limits.compact_rejected_submissions` off to on | retry strategy |
| `read6k` | `retrieval.max_read_chars` 18000 to 6000 | how much of a report one read returns |
| `norule` | task copy without the `quantified_depth` subset rule | validation rule sensitivity |
| `tokens16k` | `limits.max_completion_tokens` 8192 to 16384 | the reply cap behind the cut-off failures. **Not run by default**, see Related work |

The baseline is not run again here. The five repeats from `experiments/endometrial_determinism`
use the same config, so they give the baseline and show how much two identical runs differ.
An arm only counts as different from the baseline if it falls outside that spread.

## Files

| File | What it is |
|---|---|
| `base.yaml`, `roster_annotated50.csv` | The baseline config and the 50 annotated patients (swap the roster to use more). |
| `make_arms.py` | Writes `arm_*.yaml` and the task copy, and checks each arm differs from the base in one place. |
| `arm_*.yaml`, `task_no_depth_subset.yaml` | The generated configs. Regenerate with `make_arms.py`, do not edit by hand. |
| `run_arms.sbatch`, `run_arms.sh` | One Slurm job: serve once, then run the arms one after another, each into `<output>/<arm>`. |
| `compare_arms.py` | Compares each arm with the baseline repeats and flags the measures that fall outside the spread of the repeats. |
| `failure_review.py` | Lists every patient a run left without an answer and sorts each into a cause. Rerun it on any later run to see whether those failures went away. |

## Run it

```bash
python experiments/endometrial_agentic_diagnosis/make_arms.py
sbatch --exclude=r002,o001 --time=02:30:00 --cpus-per-task=32 \
  --export=ALL,ONCOTRACE_OUTPUT=/path/to/new/run_folder \
  experiments/endometrial_agentic_diagnosis/run_arms.sbatch
```

Arms are ordered most important first (`ARMS="..."` to choose), so a job cut short by the
time limit still leaves finished arms, and resubmitting to the same folder resumes the rest.
Keep 32 CPUs: with 16 the model server generated 25 to 50 tokens/s, against about 127 with 32 (roughly 3 to 5 times slower; measured once).

## Analyse it

Once both the baseline repeats (`experiments/endometrial_determinism`) and the arms have run:

```bash
python experiments/endometrial_agentic_diagnosis/compare_arms.py \
  --baseline-dir /path/to/baseline_run_folder --arms-dir /path/to/arms_run_folder \
  --label first_comparison
```

`results/<label>/` gets `report.md`, `arms_vs_baseline.csv` (every measure, the arm's value, the
baseline range, and whether the arm falls outside it), `patients_that_changed.csv` (patients whose
outcome differs from the baseline's most common one, and whether the baseline itself was unstable
there) `no_answer_reasons.csv` and `mcnemar_vs_baseline.csv` (for each arm and each baseline repeat, the patients where only one of the two agrees with the annotation, and the exact McNemar p-value on them; with 50 patients a p-value is only a rough guide). Read the changed patients where the baseline is stable first:
a change where the baseline already flips between repeats says nothing about the setting.

## Related work in this repo (what this experiment does not repeat)

- **`endometrial_failure_modes`** already analysed why patients had no answer in the issue 9
  run, and inspected individual patients. It found that call-budget exhaustion is a refusal
  loop on one citation group and that cut-off patients lose three replies in a row. This
  experiment cites that and adds only `failure_review.py`, which counts every no-answer patient
  in both issue 9 runs (agentic 43, one_shot 50) and can be rerun on a changed setting.
- **The reply-cap test is not repeated here.** `endometrial_failure_modes/findings/failure-test-proposal.md`
  proposes it with a preset pass line (12 patients, cap 32768) that needs mentor approval, and
  `evidence_following` lists a 16384 rerun as a next step. Agree with them before running
  `tokens16k` (`ARMS="tokens16k"`), so it is run once, with one agreed design.
- **`evidence_following`** asks a different question (does the answer follow the report text),
  so it is not repeated either.
- Nobody has yet run the call-budget, retry, read-size or rule-removal arms.

## Things to know before reading the results

- **50 annotated patients is small, and 45 of them are `present`.** A difference of one to
  three patients cannot be told from the run-to-run spread. Read results as indications,
  and rerun on more patients as annotation grows (the roster file is the only thing to swap).
- **Pin the OncoTrace commit and record it.** Use one commit for every arm and the baseline;
  results from different commits must not be compared. The contract digest does not change
  when a validation rule is removed, so OncoTrace will not stop runs from being pooled by
  mistake: keep each arm in its own folder.
- **Arms share one server, run one after another.** Prefix caching on the server can make
  later arms faster, which affects time, not the setting under test.
- The `norule` arm tests whether the rule costs effort or catches real mistakes. It cannot
  say whether the rule is clinically right, only what changes when it is gone.
