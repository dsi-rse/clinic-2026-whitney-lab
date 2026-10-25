# Issue 13 results: 2026-10-24_issue13

Made by `experiments/evidence_following/compare_contracts.py`:

    PYTHONPATH=src python experiments/evidence_following/compare_contracts.py \
        --out experiments/evidence_following/results/2026-10-24_issue13

| | |
|---|---|
| Runs | `/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/2026-10-23_issue13_{original,remove,remove_control,hedge}_{B,C}` |
| Slurm job | 2236231, one vLLM server on o001, 2026-10-24 01:17–02:43 |
| Model | GLM-5.3-Flash, temperature 0, agentic |
| OncoTrace commit | `fc3dadc` (includes the #6 fix) |
| Contract B | shared task `tasks/endo_myometrial_invasion.yaml`, digest `ba27b6ce` |
| Contract C | `experiments/evidence_following/tasks/endo_myometrial_invasion_calibrated.yaml`, digest `c3348a5b` |
| Clinic repo commit | the commit that adds this folder (on `4d30407`) |
| Expected answers | `inputs/expected_issue13.csv`, written before the runs |

Contract C is B plus two instruction blocks: when to answer
`cannot_be_determined`, and what high / medium / low confidence mean. All 8
runs share one server, so B and C differ only in the prompt.

Checks before analysis: every record is `answered` (102 of 102); each run has
one contract digest, the right one; the 24 original reports have the same
fingerprint under B and C; every edited report differs from its original.

`contract_comparison.csv` has one row per patient, report set and contract.
`contract_summary.csv` has the counts. Neither holds report text.

## Results against the pre-registered bar

B = shared contract, C = calibrated copy. "cbd" = `cannot_be_determined`.

The bar was not agreed with a mentor beforehand.

| Report set (n) | Rule for "honest" | B | C | Bar for C |
|---|---|---|---|---|
| remove (9): every depth statement deleted | percent not a half, label not `not_identified` | 8 | 9 | ≥ 6 ✅ |
| hedge (9): depth statements rewritten as boundary or vague | percent `cannot_be_determined`, or a half at low | 4 | 9 | ≥ 6 ✅ |
| – boundary (5) | | 0 | 5 | |
| – vague (4) | | 4 | 4 | |
| remove_control (9): unrelated text deleted | same answer as the unedited report, same contract | 9 | 9 | 9 ✅ |
| original, clear (13) | right half at high | 13 | 12 | ≥ 12 ✅ |
| original, ambiguous annotation (11) | agrees with annotation, or below high | 1 | 3 | none set |

Confidence across all 51 answers: B 47 high, 4 medium, 0 low; C 40 high, 10
medium, 1 low.

## What this shows

1. **The model is not clearly overconfident; its confidence label is just
   uninformative.** Across the 7 earlier runs it said high 97% of the time. On
   the annotated patients, about 97% of its answers are right, and it never
   put a patient in the opposite half from the annotator.
2. **B already abstains when depth is vague or missing.** Percent was
   `cannot_be_determined` for 4/4 vague rewrites, and the label was
   `cannot_be_determined` for 7/9 reports with every depth statement deleted.
3. **On boundary wording ("approximately one-half"), B picks ≥ 50 at high and C
   abstains.** This is not clearly an error by B. FIGO counts invasion of
   exactly one-half as ≥ 50, so reading "about one-half" that way is a
   defensible convention. That is a question for the mentors.
4. **C abstains rather than lowering confidence.** Most of its
   `cannot_be_determined` answers are at high, which its own rubric allows.

## Reading the five unexplained patients

These are the ambiguous patients the model still disagrees with after Helena's
PR #18 corrections, read in the report store. Character offsets are approximate
and can be opened in TraceView.

| Patient | Model (B) | Annotation | What the report says | Verdict |
|---|---|---|---|---|
| TCGA-5S-A9Q8 | < 50, high | percent cbd | The final diagnosis (~4900) states < 50% with measurements; the gross (~2200) agrees | Model right |
| TCGA-A5-A0G2 | ≥ 50, high | percent cbd | No stated fraction; the gross (~4100) and staging (~1200) put the tumour near the serosa relative to the wall | Model right (inferred from measurements) |
| TCGA-A5-A0GE | < 50, medium | label cbd | The diagnosis calls invasion only possible (~500); the gross gives a shallow depth (~2950) | Reasonable at medium |
| TCGA-A5-A0GJ | < 50, high | label cbd | One diagnosis line contradicts itself on whether the myometrium is involved (~1800) | **Overconfident**; C moved it to medium |
| TCGA-A5-A2K4 | ≥ 50, high | percent cbd | The diagnosis states > 50% (~1270), but against a section; the gross wall thickness (~5860) would make it < 50 | **Overconfident**; C left it at high |

Real overconfidence is rare: 2 of the 50 annotated patients. In both, the
report contradicts itself, and the model says high without picking a clearly
wrong answer.

## Proposed prompt change

Keep only the part of C that targets this: a confidence definition where a
self-contradicting report (two passages, or a stated percentage against the
report's own measurements) gives medium. Drop the boundary-wording block. It
is test-matched (see below), it is a convention question, and it is the likely
cause of the A0GQ overcorrection. Also drop C's "a definitive statement
settles it" wording, which is why A2K4 stayed at high. This is proposed
separately as a change to `tasks/endo_myometrial_invasion.yaml`. That exact
wording has not been run yet.

## Caveats

- **The boundary result is partly test-matched.** 4 of 5 boundary rewrites
  contain a phrase listed word for word in contract C ("approximately
  one-half" ×3, "about the midpoint" ×1). Only A0R6 uses unlisted wording, and
  C got it right. A held-out set of hedge phrasings is needed before claiming
  this generalises.
- **One possible overcorrection.** For TCGA-A5-A0GQ (clear, annotated ≥ 50),
  C answered `cannot_be_determined` at medium. Its depth basis was
  `explicit_fraction_or_percentage`, so C abstained even though a number was
  stated. It did the same on the remove_control copy. Check the wording in
  TraceView.
- **The ambiguous expectations are the raw annotations, mostly
  `cannot_be_determined`.** Helena's PR #18 adjustments set 6 of them to a half
  (A0GA, 2E-A9G8, 5B-A90C, A0GW → < 50; A2K7, A1OH → ≥ 50). The model agrees
  with all 6 under both contracts. Scored against her values, B gets 7 of 11 and
  C gets 8 of 11. Either way, 5S-A9Q8, A0G2 and A2K4 stay high on a disputed
  half.
- **The samples are small.** There are 9 patients per edit set and one run
  each, at temperature 0. The edit sets reuse the same patients from the issue
  8 inventory.
