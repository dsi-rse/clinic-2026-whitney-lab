# Evidence-following results: 2026-10-20_170241

Made 2026-10-20T22:02:41+00:00 by `experiments/evidence_following/run_experiment.py`.

| | |
|---|---|
| Original run | `/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/2026-10-09_endometrial_glm53` (376 records) |
| Control reruns | `2026-10-13_issue8_s1_control`, `2026-10-13_issue8_s2_control`, `2026-10-13_issue8_s3_control` |
| Edit arms | flip `2026-10-13_issue8_flip`, reword `2026-10-13_issue8_reword` |
| OncoTrace commit of the runs | `e901b3f` |
| Clinic repo commit | `c78b7d1` |

All numbers are in `summary.txt`; the tables are the CSV and JSON files here.
What each file holds is in the experiment README.

## Key findings

As of 2026-10-20, with GLM-5.3-Flash on OncoTrace `e901b3f`:

1. GLM-5.3-Flash always reads the data before coming to a conclusion.
2. GLM-5.3-Flash does at least a decent job using the data in forming its
   conclusions: when we flipped every depth statement in a report, its answer
   flipped too.
3. GLM-5.3-Flash very rarely says it cannot come to a conclusion.

**When a report states depth clearly, the answer follows the text.** Flipping
every depth statement to the other half flipped the answer in 9 of 9 patients.
Rewording the same statements changed nothing in 9 of 9. Unedited reruns changed
1 answer in 67.

**The open weakness is ambiguous or missing evidence.** The model almost never
answers `cannot_be_determined`, and its stated confidence doesn't reflect when
it's unsure.

## Part 1: what the original run shows

Original run: 376 of the 546 roster patients (345 answered, 31 no answer),
including all 50 annotated patients. Numbers are from `summary.txt`.

1. **Label accuracy says little.**
   - 45 of 50 annotated patients are `present`. Of the 41 answered annotated
     patients, the label agrees in 38; answering `present` every time would
     score 36.
   - The percent field (`<50` / `≥50`) is the informative one: 30 of 41 agree,
     against 16 for always guessing the most common half.
2. **When the model commits to a half, it never contradicts the annotator:** 0
   swaps between `less_than_50` and `fifty_or_greater`.
3. **It almost never says `cannot_be_determined`.**
   - The annotator used it 13 times (3 for the label, 10 for the percent). The
     run picked a definite value every time.
   - Some of these look like conservative annotations, where the report gives
     numbers. Others look like over-commitment on hedged wording (TCGA-A5-A0GE,
     -A0GJ).
4. **Reading is not the bottleneck.** In all 376 records the model read the
   whole report before its first submit attempt.
5. **Contract refusals change citations, not answers.** In 221 patients whose
   first submit was refused, the label and percent never changed before the
   answer was accepted.
6. **It cites more broadly than the annotator.**
   - Median 3 depth citations, against the annotator's 1–2.
   - Some are lymphovascular-invasion statements, which the contract excludes
     from depth.
7. **Depth evidence is usually redundant.** In 24 of 28 reports checked, depth
   appears in two or more independent places (diagnosis, synoptic, gross,
   comment, stage). So removing one cited passage rarely removes the support.
8. **No-answers are a harness problem, not missed evidence.**
   - 22 of 31 no-answers looped on refused submits until the 24-call budget ran
     out. The other 9 were cut off at `max_completion_tokens` 8192.
   - The largest cause is
     [dsi-rse/oncotrace#5](https://github.com/dsi-rse/oncotrace/issues/5): a
     citation list sent as a JSON *string* is checked one character at a time.
     Fix: [dsi-rse/oncotrace#6](https://github.com/dsi-rse/oncotrace/pull/6).

### Five annotated patients

Every citation in all 345 answered records opens at the right words in
TraceView (checked separately with `check_traceview_citations.py`, which needs a
running TraceView, so it is not part of `run_experiment.py`).

| Patient | Field (reference → run) | Run's depth citations | Matches the annotated passage? | Conflicting text |
|---|---|---|---|---|
| TCGA-A5-A2K2 | percent `<50` → `<50` | `[957,1107)`; quantified `[1005,1057)` | Yes: covers annotated `[957,1000)` and `[1005,1057)` | Gross `[8980,9158)` and intraoperative `[16390,16438)` show no definite gross invasion. The run cites both as counterevidence. |
| TCGA-A5-A0GQ | percent `≥50` → `≥50` | stage `[1112,1158)`, gross `[2935,3020)`, `[3025,3064)`, `[1025,1062)` | No: the annotated line `[943,1022)` is the run's *counterevidence* | That diagnosis line uses boundary wording. Stage and gross settle the half. |
| TCGA-A5-A2K4 | label `cannot_be_determined` → `present`/`≥50` | `[1257,1402)`, `[1405,1469)` | No: the annotated `[5507,5619)` falls inside run counterevidence `[5483,5619)` | The run records 3 counterevidence passages |
| TCGA-A5-A0GE | percent `cannot_be_determined` → `<50` | `[514,643)`, `[2884,3061)` | Partly: `[514,643)` matches exactly; the quantified passage is not annotated | No counterevidence cited |
| TCGA-A5-A0GU | percent `<50` → `no_answer` | – | – | One read covered the whole report. The 22 submit attempts were all refused on the quote `[` (the bug in #5). |

## Part 2: does the answer change when the evidence changes?

Design is in the experiment README. Numbers are from `arm_comparison.csv` and
`control_noise.csv`.

| Arm | Result |
|---|---|
| **Flip** | **9 of 9 moved to the other half** (6 `<50`→`≥50`, 3 `≥50`→`<50`). Label stayed `present` and confidence stayed `high`. 23 of 26 depth citations land on edited passages. |
| **Reword** | **9 of 9 unchanged.** 27 of 29 depth citations land on the reworded passages. |
| **Unedited reruns** | 23 of 24 patients gave the same answer in every run where they answered. Across all reruns, 1 changed answer in 67 answered units. For the 9 flip patients, 0 changes in 27 rerun comparisons. |

**Checks:**
- Projection fingerprints match the original run for all 24 unedited patients,
  and differ for all 9 flip and 9 reword patients, so the edits reached the
  model.
- In flipped reports, the unedited gross, intraoperative or frozen-section
  passages that now disagree (TCGA-A5-A0G1, -A2K2, -A0R6) are cited as
  counterevidence. The answer follows the edited final diagnosis.

**The one unstable patient: TCGA-A5-A0G2.**
- It answered `≥50` in 3 runs and percent `cannot_be_determined` in 1, with
  `high` confidence both ways.
- That is the only `cannot_be_determined` the model has produced, and it matches
  the annotation.

**Noise is in completion, not answers.**
- 5 of 72 rerun units ended `no_answer`, each a different patient.
- 3 were the bug in #5, 1 was a quote-matching loop on a real quote, and 1 was
  truncation.

## Limits

- 9 edited patients, 8 from one site. One run per edit arm.
- The annotations (50 patients, one annotator, not adjudicated, 45 from site
  TCGA-A5) are a development reference, not a test set.
- The edits were drafted with Claude and haven't had mentor review.
- Changing *every* statement consistently is the easiest version of the test.
- The original run is partial (376 of 546); it hit the 12 h job limit.
