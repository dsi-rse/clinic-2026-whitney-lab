# Evidence-buckets results: 2026-11-17_213905

Made 2026-11-18T03:39:05+00:00 by `experiments/evidence_buckets/compare_arms.py --run baseline_rep1=/Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs/2026-11-18_evidence_buckets_baseline/rep1 --run baseline_rep2=/Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs/2026-11-18_evidence_buckets_baseline/rep2 --run evidence_rep1=/Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs/2026-11-18_evidence_buckets_evidence/rep1 --run evidence_rep2=/Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs/2026-11-18_evidence_buckets_evidence/rep2`.

| | |
|---|---|
| Runs | baseline_rep1 `rep1` (66 records), baseline_rep2 `rep2` (66 records), evidence_rep1 `rep1` (66 records), evidence_rep2 `rep2` (66 records) |
| OncoTrace commit | `d4b7fd3` |
| Task contracts | `3d75c051`, `4e4fe0ea` |
| Clinic commit | `0f1306b` |

The run folders were made on a laptop through OpenRouter and are not yet on the
shared cluster path; `provenance.json` records this as acknowledged. All numbers
are in `summary.txt`; the tables are the CSV files here. What each table holds
is in the experiment README.

## Findings

"Invasion" is the myometrial invasion answer; "depth" is whether invasion
reaches half the myometrium. A flagged answer is `implied_*` or `uncertain`.

- **The model sorted almost everything into Confident.** In the evidence runs,
  66 and 65 of 66 invasion answers and 53 and 50 of 66 depth answers were
  `explicit`. The other depth answers were 9 and 12 `implied_high`, 1
  `uncertain` and 3 `not_applicable` (`categories.csv`). No answer used
  `implied_medium` or `implied_low`.
- **Not present was never used, and Uncertain once per run.** No run in either
  arm answered `cannot_be_determined` for invasion or depth, and the evidence
  runs answered depth `uncertain` once each (`per_run.csv`). So the feared easy
  way out did not happen: no patient with a definite annotation got
  `cannot_be_determined` (`definite_annotation_model_cbd.csv` is empty).
- **The flags point at the right depth answers, but they miss most of the
  annotator's undetermined cases.** Flagged depth answers were 10 and 13 of 66
  but held 6 of 14 and 5 of 13 depth disagreements (`flagged_share.csv`).
  Explicit depth answers agreed with the annotations in 45 of 53 and 42 of 50
  cases, against 53 and 52 of 66 for the baseline runs (`categories.csv`,
  `four_way.csv`). But all 3 patients the annotator left undetermined for
  invasion got `present`, and all 11 undetermined for depth got a definite
  depth, in every run (`annotated_cbd_split.csv`). Of the 12 over-committed
  depth answers per evidence run, 6 and 7 were labelled `explicit`
  (`categories.csv`).
- **Adding the categories did not change the main answers beyond run-to-run
  noise.** Between arms, 1 or 2 patients changed answer per pair of runs; the
  two baseline runs differed on 1, and the two evidence runs on 3. Every
  patient that changed between arms also changed between two runs of the same
  arm (`pass_bar.csv`, `answer_changes.csv`).
- **The review queue would be 10 or 13 patients of 66**, of whom 7 and 6 have
  an answer that disagrees with the annotations. Another 8 patients per run
  disagree without being flagged (`review_queue.csv`).
- **#42's A0GJ** got `present` / `explicit` and `less_than_50` /
  `implied_high` in both evidence runs; the annotation is undetermined for
  both (`watched_patients.csv`).

### Pass bar (set in issue #55 before the runs; `pass_bar.csv`)

- **Useful:** met for depth in both runs (flagged share of disagreements 0.429
  and 0.385 against 0.152 and 0.197 of answers; explicit agreement 0.849 and
  0.840 against 0.795). For invasion it is inconclusive: 0 and 1 invasion
  answers were flagged.
- **Safe:** the strict test fails in 3 of 4 pairs, by one patient each (2
  changed against 1 between the baseline runs). Because every changed patient
  also changes within an arm, we read this as run-to-run variation, not an
  effect of the contract. One baseline pair is too small a reference to say
  more.

**So what:** the categories add a useful flag on depth, but they do not
replace the annotator's judgment on undetermined reports. The model calls most
of those answers `explicit`.
