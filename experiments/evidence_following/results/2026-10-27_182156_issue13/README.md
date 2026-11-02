# Issue 13 results: 2026-10-27_182156_issue13

Made 2026-10-27T23:21:57+00:00 by `experiments/evidence_following/compare_contracts.py --label issue13`.

| | |
|---|---|
| Runs | original_B `2026-10-23_issue13_original_B` (24 records), original_C `2026-10-23_issue13_original_C` (24 records), remove_B `2026-10-23_issue13_remove_B` (9 records), remove_C `2026-10-23_issue13_remove_C` (9 records), remove_control_B `2026-10-23_issue13_remove_control_B` (9 records), remove_control_C `2026-10-23_issue13_remove_control_C` (9 records), hedge_B `2026-10-23_issue13_hedge_B` (9 records), hedge_C `2026-10-23_issue13_hedge_C` (9 records) |
| OncoTrace commit | `fc3dadc` |
| Task contracts | `ba27b6ce`, `c3348a5b` |
| Clinic commit | `fd0c639` |
| Expected answers | `inputs/expected_issue13.csv`, written before the runs |
| Earlier runs (confidence tally) | `2026-10-09_endometrial_glm53`, `2026-10-13_issue8_flip`, `2026-10-13_issue8_reword`, `2026-10-13_issue8_s1_control`, `2026-10-13_issue8_s2_control`, `2026-10-13_issue8_s3_control` |

All numbers are in `summary.txt`; the tables are the CSV files here. What each
file holds is in the experiment README.

`contract_comparison.csv` has one row per patient, report set and contract.
`contract_summary.csv` has the counts, with `honest` scored against the raw
annotations and `honest_pr18` against PR #18's revised depth values.
`confidence_by_run.csv` is the stated-confidence mix per run. None holds
report text.

## Findings

<!-- Kaden: these are Claude's words from the tables. Replace them with your own. -->

Every number below is from `contract_summary.csv` or `confidence_by_run.csv` in
this folder. B = the shared contract, C = the calibrated copy. "cbd" =
`cannot_be_determined`. The pass bar was Kaden's, not agreed with a mentor.

| Report set (n) | Rule for "honest" | B | C | Bar for C |
|---|---|---|---|---|
| remove (9): every depth statement deleted | percent not a half, label not `not_identified` | 8 | 9 | ≥ 6 ✅ |
| hedge (9): depth rewritten as boundary or vague | percent cbd, or a half at low | 4 | 9 | ≥ 6 ✅ |
| – boundary (5) | | 0 | 5 | |
| – vague (4) | | 4 | 4 | |
| remove_control (9): unrelated text deleted | same answer as the unedited report, same contract | 9 | 9 | 9 ✅ |
| original, clear (13) | right half at high | 13 | 12 | ≥ 12 ✅ |
| original, ambiguous (11), vs the raw annotations (`honest`) | agrees, or disagrees below high | 1 | 3 | none set |
| original, ambiguous (11), vs PR #18's values (`honest_pr18`) | agrees, or disagrees below high | 7 | 8 | none set |

1. **The confidence label is almost constant, so it carries little
   information.** Over the 6 earlier GLM-5.3-Flash runs on real reports it was
   `high` in 416 of 430 answered records (96.7%, `confidence_by_run.csv`), with
   14 `medium` and no `low`. Here it is `high` in 47 of 51 answers under B and
   40 of 51 under C. Caveats: those 6 runs predate dsi-rse/oncotrace#6
   and ran OncoTrace `e901b3f` on contract `940b2a7b`, so they are a different
   setting from the 8 runs here; `provenance.json` records each one. The two
   2026-10-09 smoke runs are left out because their units are synthetic
   `SMOKE-NNNN` rather than pathology reports; including the GLM one would give
   419 of 433 (96.8%), so it changes nothing but the denominator's meaning.
2. **B does not abstain on the real ambiguous reports.** On all 11 ambiguous
   patients both contracts gave a definite half — `percent_cbd` is 0 for both —
   and B was `high` for 10 of the 11. Against the raw annotations that is 1 of
   11 honest.
3. **Most of those definite halves look right, not overconfident.** Scored
   against PR #18's revised depth values, B gets 7 of 11 and C 8 of 11: the
   annotations were more cautious than the evidence required for 6 patients
   (A0GA, 2E-A9G8, 5B-A90C, A0GW, A2K7, A1OH), and the model agrees with all 6
   under both contracts. Two of the six are inferences from #18's tables rather
   than values #18 states; see `pr18_source` in `inputs/expected_issue13.csv`.
   Reading the 5 that remain by hand (below) leaves 2 patients that are real
   overconfidence.
4. **B already abstains when depth is missing or vague.** Percent was cbd for
   4/4 vague rewrites, and the label was cbd for 7/9 reports with every depth
   statement deleted.
5. **On boundary wording B picks a half at high and C abstains (0/5 → 5/5).**
   This is not clearly an error by B: FIGO counts invasion of exactly one-half
   as ≥ 50, so reading "about one-half" that way is a defensible convention.
   That is a question for the mentors. The gain is also partly test-matched
   (see the caveats).
6. **C abstains rather than lowering confidence.** Most of its cbd answers are
   at `high`, which its own rubric allows.

### Reading the five patients that PR #18 does not explain

The ambiguous patients the model still disagrees with after #18. Read in the
report store; character offsets are approximate and can be opened in TraceView.

| Patient | Model (B) | Annotation | Where it is | Verdict |
|---|---|---|---|---|
| TCGA-5S-A9Q8 | < 50, high | percent cbd | final diagnosis ~4900, gross ~2200 agrees | Model right |
| TCGA-A5-A0G2 | ≥ 50, high | percent cbd | no stated fraction; gross ~4100, staging ~1200 | Model right (inferred from measurements) |
| TCGA-A5-A0GE | < 50, medium | label cbd | diagnosis ~500 calls invasion only possible; gross ~2950 | Reasonable at medium |
| TCGA-A5-A0GJ | < 50, high | label cbd | one diagnosis line contradicts itself ~1800 | **Overconfident**; C moved it to medium |
| TCGA-A5-A2K4 | ≥ 50, high | percent cbd | diagnosis ~1270 states > 50% against a section; gross wall ~5860 implies < 50 | **Overconfident**; C left it at high |

Real overconfidence is rare: 2 of the 50 annotated patients. In both the report
contradicts itself, and the model says `high` without picking a clearly wrong
half.

### Proposed prompt change

Keep only the part of C that targets this: a confidence definition where a
self-contradicting report (two passages, or a stated percentage against the
report's own measurements) gives `medium`. Drop the boundary-wording block — it
is test-matched, it is a convention question, and it is the likely cause of the
A0GQ overcorrection. Also drop C's "a definitive statement settles it" wording,
which is why A2K4 stayed at `high`. This belongs in a change to
`tasks/endo_myometrial_invasion.yaml`, and that exact wording has not been run.

### Caveats

- **The boundary result is partly test-matched.** 4 of 5 boundary rewrites
  contain a phrase listed word for word in contract C ("approximately
  one-half" ×3, "about the midpoint" ×1). Only A0R6 uses unlisted wording, and
  C got it right. A held-out set of hedge phrasings is needed before claiming
  this generalises.
- **One possible overcorrection.** For TCGA-A5-A0GQ (clear, annotated ≥ 50), C
  answered cbd at medium. Its depth basis was
  `explicit_fraction_or_percentage`, so C abstained even though a number was
  stated. It did the same on the remove_control copy. Check the wording in
  TraceView.
- **Two expectation sets, neither adjudicated.** `honest` uses Mariam's raw
  annotations, which are mostly cbd for depth; `honest_pr18` uses #18's
  revised values, which are Helena's reading and not reviewed by Mariam or a
  mentor. The real number is somewhere between 1/11 and 7/11 for B.
- **Stability is not measured here.** Issue #13 asks for the ambiguous
  patients on 3 separate server starts; these 8 runs share one (job 2236231).
  The temperature repeats in #21 are one server start at a different setting,
  so they do not cover it.
- **The samples are small.** 9 patients per edit set, one run each, at
  temperature 0, and the edit sets reuse the same patients from the issue 8
  inventory.
