# Three failure examples and one proposed test

Run `endometrial_glm53_20261012` (498 of 546 records at the time). Facts come
from TraceView's loaded records; this file holds counts, IDs and offsets only,
no report text. Related notes: [patient-inspections.md](patient-inspections.md).

## Three examples

| Patient | Failure | Why chosen |
|---|---|---|
| TCGA-A5-A0GE | `truncated_without_tool_call`: 3 replies, all cut off at 8192 tokens, no submission | Cleanest truncation case (no refusals at all). It is annotated (`cannot_be_determined`), so we know what a correct answer looks like. |
| TCGA-AX-A06F | `model_call_budget_exhausted`: 19 refused quotes, every one a 1-character quote for `depth_evidence` | The clearest case of the 1-character quote pattern (454 of the 510 `citation_quote_not_found` refusals in budget-exhausted patients are single characters). Not annotated. |
| TCGA-A5-A0GP | `model_call_budget_exhausted`: 18 refusals of one 181-character quote (best verbatim match 0.47), plus 4 one-character ones | Shows a different loop: a near-verbatim quote resubmitted rather than corrected. It is annotated (`present`), so the lost answer has a known value. |

All three had the whole report read (read ranges cover 100% of the document), so
none is a case of unread text.

## What the records say about truncation

- All 12 `truncated_without_tool_call` patients had exactly 3 truncated replies.
  That matches the code: an initial reply plus `completion_passes: 2` nudges, then
  the unit is closed (`oncotrace/agent.py`). A nudge asks again with the same
  8192-token cap, so it gives the model no extra room.
- These replies are unusually long: median 29,820 characters of reasoning
  (36 replies), against a median of 158 for ordinary replies in answered patients.
- They do not look like loops: the share of repeated 100-character chunks is 0
  at the median (maximum 0.16 for a single reply).
- Truncation is not always fatal: 106 answered patients had at least one
  truncated reply and then finished.
- The config sets `temperature: 0.0` and `reasoning_effort: max`.

## Proposed test

**Explanation under test:** these patients fail because the 8192-token cap is too
small for the model's reasoning, not because the model cannot decide or loops.

**Test:** rerun only the 12 patients, changing only `max_completion_tokens` from
8192 to 32768. Everything else stays as in `config/endometrial.yaml`
(`temperature: 0.0`, `reasoning_effort: max`, 24 calls, 2 completion passes).
Prompt plus 32768 should fit the server's `max_model_len` of 49152 (peak prompt
seen was about 22k tokens, so confirm it fits for the longest report).

Patients: TCGA-A5-A0GE, TCGA-AJ-A3EM, TCGA-AX-A1C7, TCGA-AX-A1CI, TCGA-B5-A11S,
TCGA-D1-A17M, TCGA-DF-A2KN, TCGA-DF-A2KS, TCGA-DF-A2L0, TCGA-DI-A0WH,
TCGA-DI-A1NN, TCGA-EY-A1G7.

**What to measure (mechanical, set before running):**
1. Does the first reply end with a tool call (`finish_reason` not `length`)?
2. Its completion-token count against the new cap.
3. Does the unit end with an accepted answer, and what label and confidence?

**If the explanation is right:** most replies finish below the new cap, with
token counts in the range of roughly 8k-25k, and the patients then reach a
submission. **It is wrong if** most still hit 32768 (then the model is not
limited by room, and a bigger cap only costs more), or if they finish but are
then refused or give different labels each time.

Proposed pass line: at least 9 of 12 finish a reply with a tool call. This is a
scientific threshold, so it needs the mentor's approval before the run, and the
result should be reported against it exactly as set.

**Why this test, and what it cannot show:** temperature 0 makes a plain rerun at
8192 likely to repeat the failure, so no same-cap control arm is proposed. It
also cannot say whether `reasoning_effort: max` is the better thing to change, or
whether longer reasoning gives better answers. A follow-up could rerun the
same 12 at lower effort. With 12 patients and one annotated (A5-A0GE), it tells
us whether room is the bottleneck, not whether the labels are right.

**Needs:** the lab's GLM server endpoint from the mentor, and a Slurm GPU job.
No code in this repo changes; it is a config value.

## Output location

- This proposal: `experiments/endometrial_failure_modes/findings/failure-test-proposal.md`.
- The test's records, if approved, go in a new run folder outside Git, for
  example `~/oncotrace-work/runs/endometrial_glm53_trunc32k/`. The completed
  run's records are never edited. Summarize them by running the experiment
  again with a new label (see the experiment's README).
