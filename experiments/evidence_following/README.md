# Does OncoTrace follow the evidence? (issue #8)

**Question:** when OncoTrace answers the myometrial-invasion task, does the answer come from the report text, or from a prior that it then justifies with citations?

**Short answer:**
- **When a report states depth clearly, the answer follows the text.** Flipping every depth statement to the other half flipped the answer in 9 of 9 patients. Rewording the same statements changed nothing in 9 of 9. Unedited reruns changed 1 answer in 67.
- **The open weakness is ambiguous or missing evidence.** The model almost never answers `cannot_be_determined`, and its stated confidence doesn't reflect when it's unsure.

No report, rationale, or annotation text appears here. Patients are TCGA IDs, and passages are half-open character offsets `[start, end)` into the patient's single report document.

## Setup

**Model and harness:**
- GLM-5.3-Flash, agentic mode, run with oncotrace `e901b3f`.
- Task contract: [`tasks/endo_myometrial_invasion.yaml`](../../tasks/endo_myometrial_invasion.yaml). Config: `config/endometrial.yaml` with temperature 0.

**Runs:**
- Original run: 376 of the 546 roster patients, including all 50 annotated patients.
- Experiment runs: 5 more, each on its own server start.

**Reference annotations:**
- 50 patients in [`annotations/`](../../annotations/endo_myometrial_invasion/), from one annotator and not adjudicated.
- 45 of the 50 come from one tissue source site (TCGA-A5).

## Part 1: what the existing run shows

1. **Label accuracy says little.**
   - 45 of 50 annotated patients are `present`. Of the 41 answered annotated patients, the label agrees in 38; answering `present` every time would score 36.
   - The percent field (`<50` / `≥50`) is the informative one: 30 of 41 agree, against 16 for always guessing the most common half.
2. **When the model commits to a half, it never contradicts the annotator:** 0 swaps between `less_than_50` and `fifty_or_greater`.
3. **It almost never says `cannot_be_determined`.**
   - The annotator used it 13 times (3 for the label, 10 for the percent). The run picked a definite value every time.
   - Some of these look like conservative annotations, where the report gives numbers. Others look like over-commitment on hedged wording (TCGA-A5-A0GE, -A0GJ).
4. **Reading is not the bottleneck.** In all 376 records the model read the whole report before its first submit attempt.
5. **Contract refusals change citations, not answers.** In 221 patients whose first submit was refused, the label and percent never changed before the answer was accepted.
6. **It cites more broadly than the annotator.**
   - Median 3 depth citations, against the annotator's 1–2.
   - Some are lymphovascular-invasion statements, which the contract excludes from depth.
7. **Depth evidence is usually redundant.** In 24 of 28 reports checked, depth appears in two or more independent places (diagnosis, synoptic, gross, comment, stage). So removing one cited passage rarely removes the support.
8. **No-answers are a harness problem, not missed evidence.**
   - 22 of 31 no-answers looped on refused submits until the 24-call budget ran out. The other 9 were cut off at `max_completion_tokens` 8192.
   - The largest cause is [dsi-rse/oncotrace#5](https://github.com/dsi-rse/oncotrace/issues/5): a citation list sent as a JSON *string* is checked one character at a time. Fix: [dsi-rse/oncotrace#6](https://github.com/dsi-rse/oncotrace/pull/6).

### Five annotated patients

Every citation in all 345 answered records opens at the right words in TraceView (`check_traceview_citations.py`).

| Patient | Field (reference → run) | Run's depth citations | Matches the annotated passage? | Conflicting text |
|---|---|---|---|---|
| TCGA-A5-A2K2 | percent `<50` → `<50` | `[957,1107)`; quantified `[1005,1057)` | Yes: covers annotated `[957,1000)` and `[1005,1057)` | Gross `[8980,9158)` and intraoperative `[16390,16438)` show no definite gross invasion. The run cites both as counterevidence. |
| TCGA-A5-A0GQ | percent `≥50` → `≥50` | stage `[1112,1158)`, gross `[2935,3020)`, `[3025,3064)`, `[1025,1062)` | No: the annotated line `[943,1022)` is the run's *counterevidence* | That diagnosis line uses boundary wording. Stage and gross settle the half. |
| TCGA-A5-A2K4 | label `cannot_be_determined` → `present`/`≥50` | `[1257,1402)`, `[1405,1469)` | No: the annotated `[5507,5619)` falls inside run counterevidence `[5483,5619)` | The run records 3 counterevidence passages |
| TCGA-A5-A0GE | percent `cannot_be_determined` → `<50` | `[514,643)`, `[2884,3061)` | Partly: `[514,643)` matches exactly; the quantified passage is not annotated | No counterevidence cited |
| TCGA-A5-A0GU | percent `<50` → `no_answer` | – | – | One read covered the whole report. The 22 submit attempts were all refused on the quote `[` (the bug in #5). |

## Part 2: does the answer change when the evidence changes?

**Design:**
- 9 annotated patients where the run matched the annotation on both label and half: 6 `<50`, 3 `≥50`.
- Each arm reads its own edited copy of the reports, and the originals are untouched. Unit and document IDs are unchanged, so runs pair by patient.

| Arm | Edit | Expected if the model follows the evidence |
|---|---|---|
| Flip | Rewrite every definitive depth passage to the other half, consistently (17 passages, including mm figures and one stage, pT1b → pT1a) | Percent moves to the other half |
| Reword | Same passages, same meaning and half, different wording | Unchanged |
| Unedited ×3 | None; 24 patients, 3 new server starts | Unchanged (measures run-to-run noise) |

**Results:**

| Arm | Result |
|---|---|
| **Flip** | **9 of 9 moved to the other half** (6 `<50`→`≥50`, 3 `≥50`→`<50`). Label stayed `present` and confidence stayed `high`. 23 of 26 depth citations land on edited passages. |
| **Reword** | **9 of 9 unchanged.** 27 of 29 depth citations land on the reworded passages. |
| **Unedited reruns** | 23 of 24 patients gave the same answer in every run where they answered. Across all reruns, 1 changed answer in 67 answered units. For the 9 flip patients, 0 changes in 27 rerun comparisons. |

**Checks:**
- Projection fingerprints match the original run for all 24 unedited patients, and differ for all 9 flip and 9 reword patients, so the edits reached the model.
- In flipped reports, the unedited gross, intraoperative or frozen-section passages that now disagree (TCGA-A5-A0G1, -A2K2, -A0R6) are cited as counterevidence. The answer follows the edited final diagnosis.

**The one unstable patient: TCGA-A5-A0G2.**
- It answered `≥50` in 3 runs and percent `cannot_be_determined` in 1, with `high` confidence both ways.
- That is the only `cannot_be_determined` the model has produced, and it matches the annotation.

**Noise is in completion, not answers.**
- 5 of 72 rerun units ended `no_answer`, each a different patient.
- 3 were the bug in #5, 1 was a quote-matching loop on a real quote, and 1 was truncation.

**Limits:**
- 9 patients, 8 from one site.
- One run per edit arm.
- The edits were drafted with Claude and haven't had mentor review.
- Changing *every* statement consistently is the easiest version of the test.

## What's in this folder

Everything for this experiment lives here. Inputs and outputs that hold report text stay in the private workspace (`$ONCOTRACE_WORKSPACE/analysis/issue8/`), never in Git.

| File | What it does | Writes |
|---|---|---|
| `records.py` | Shared loader for runs, annotations and reports, plus span-overlap helpers. Not run directly. | – |
| `evidence_alignment.py` | Compares a run with the annotations: field agreement, cited vs annotated passages, how much was read before answering | `alignment_annotated.csv`, `alignment_spans.csv`, `reading_coverage_run.csv` |
| `triage_no_answers.py` | Classifies each `no_answer` and checks whether refusals changed answers | `no_answer_triage.csv`, `refusals_run.csv` |
| `evidence_inventory.py` | Adds citation and edit-feasibility facts to the hand-curated passage list | `evidence_inventory.json`, `edit_candidates.csv` |
| `check_traceview_citations.py` | Confirms each citation is highlighted at the right words in a running TraceView | prints only |
| `report_edits.py` | Builds an edited report copy for one arm from a hand-written spec | `inputs/<arm>/` (private) |
| `compare_arms.py` | Lines up each patient's answer across the original run, the reruns and the edit arms | `arm_comparison.csv`, `control_noise.csv` |

Run them from the repo root. Each takes `--help`, and its docstring explains the method:

```bash
P=experiments/evidence_following
python $P/evidence_alignment.py
python $P/triage_no_answers.py
python $P/evidence_inventory.py
python $P/check_traceview_citations.py --port 8742 --units TCGA-A5-A2K2 TCGA-A5-A0GQ   # TraceView must be running
python $P/report_edits.py template --arm flip --units TCGA-A5-A0GI TCGA-A5-A0GM       # then fill in replacements
python $P/report_edits.py apply --arm flip
python $P/compare_arms.py \
    --controls runs/2026-10-13_issue8_s1_control runs/2026-10-13_issue8_s2_control runs/2026-10-13_issue8_s3_control \
    --arm flip=runs/2026-10-13_issue8_flip --arm reword=runs/2026-10-13_issue8_reword
```

Defaults point at the issue 8 workspace. Set `ONCOTRACE_WORKSPACE` to use your own.

**Running an arm:**
- Use the original run config, changing only `roster:` and, for edit arms, the source `path:` (to `inputs/<arm>/ucec_pathology_report.jsonl`).
- Give each arm a fresh, empty run folder. OncoTrace skips any patient that already has a record, even when the report was edited.
- Rosters must not be empty: an empty roster means the whole store.

## Next

1. **Removal experiment:** delete all depth evidence versus delete unrelated text of the same length. The contract's expected answer is `cannot_be_determined`, which directly tests the over-commitment above. Candidates and controls are already chosen.
2. **Rerun with the #6 fix:** rerun the patients affected by #5 with the fix, and raise `max_completion_tokens` to 16384.
3. **Open questions for the mentor:**
   - Should a stage that names no edition read pT1b as AJCC 6th (`<50`) or 7th (`≥50`)?
   - Is a stage-only report `cannot_be_determined`, including when only pT2 remains?
   - How should boundary wording (about one-half, 50%) be resolved?
   - Should the experiments keep temperature 0 or move to the model's 1.0 / 0.95?
