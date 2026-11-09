# Full-cohort baseline: tables

Made by `run_analysis.py` (see ../../README.md). Only patient IDs, counts and
reason codes are in this folder. `provenance.json` records the runs and files used.
It was made from a clean checkout: the code was committed first, and the record
was made before this folder existed.

Run names: `agentic_new` and `one_shot_new` are the updated OncoTrace on all 546
patients; `agentic_issue9` and `one_shot_issue9` are the older full runs of
Issue 9; `issue17_repN` are the five repeats on the 50 annotated patients.
Cost columns count what the model did, not patients' labels.

## 1. All 546 patients: completion and cost (full_cohort/completion_and_cost.csv)
One row per run. A cell counts patients (answered, no_answer, patients_*), model
calls, or tokens. `completion_tokens_*` is what the model wrote and
`prompt_tokens_*` is what the server read (summed over calls; each call sends the
conversation again). `patients_using_all_24_calls` is patients who hit the
call limit. A cut-off reply is one stopped by the 8,192-token limit. A rejected
submission is one OncoTrace refused with a reason code. Compare `no_answer`
(smaller is better) and `calls_mean`, `tokens_median` and `prompt_tokens_median` (smaller is cheaper).

| mode | patients | answered | no_answer | calls_mean | calls_median | calls_max | patients_using_all_24_calls | completion_tokens_total | tokens_median | prompt_tokens_total | prompt_tokens_median | cut_off_replies | patients_with_cut_off | rejected_submissions | patients_with_rejection |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| agentic_new | 546 | 543 | 3 | 4.62 | 4.0 | 24 | 3 | 5099520 | 7005.0 | 15461291 | 19404.5 | 243 | 177 | 1068 | 355 |
| one_shot_new | 546 | 545 | 1 | 2.02 | 2.0 | 24 | 1 | 3969827 | 5867.0 | 6131364 | 9356.5 | 211 | 159 | 720 | 327 |
| agentic_issue9 | 546 | 503 | 43 | 5.11 | 4.0 | 24 | 26 | 4824155 | 5833.5 | 18741654 | 17636.5 | 220 | 141 | 1220 | 350 |
| one_shot_issue9 | 546 | 496 | 50 | 3.13 | 2.0 | 24 | 19 | 5891937 | 7633.0 | 13732783 | 10281.0 | 321 | 194 | 1277 | 373 |

Most common rejection codes:

| mode | top_rejection_codes |
|---|---|
| agentic_new | quantified_depth_not_classified 385; argument_not_a_list 273; answer_exists 138; citation_quote_not_found 72; submission_fields_missing 47 |
| one_shot_new | quantified_depth_not_classified 291; answer_exists 179; argument_not_a_list 71; citation_quote_not_found 56; citation_quote_ambiguous 42 |
| agentic_issue9 | citation_quote_not_found 554; quantified_depth_not_classified 358; evidence_citations_missing 79; answer_exists 61; citation_quote_ambiguous 39 |
| one_shot_issue9 | citation_quote_not_found 480; quantified_depth_not_classified 299; evidence_citations_missing 130; citation_absent 94; empty_unresolved_conflicts 67 |

## 2. The same 50 annotated patients (same_50_patients/completion_and_cost.csv)
Same columns as table 1, but every run is cut down to the 50 patients that have
manual annotations, so runs made on different cohorts can be compared.

| mode | patients | answered | no_answer | calls_mean | calls_median | calls_max | patients_using_all_24_calls | completion_tokens_total | tokens_median | prompt_tokens_total | prompt_tokens_median | cut_off_replies | patients_with_cut_off | rejected_submissions | patients_with_rejection |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| agentic_new | 50 | 50 | 0 | 4.38 | 4.0 | 11 | 0 | 453600 | 6530.5 | 1278921 | 23033.0 | 24 | 16 | 79 | 38 |
| one_shot_new | 50 | 50 | 0 | 2.04 | 2.0 | 4 | 0 | 356678 | 5728.5 | 634902 | 12498.0 | 16 | 13 | 47 | 37 |
| agentic_issue9 | 50 | 49 | 1 | 4.52 | 4.0 | 24 | 1 | 381561 | 5666.0 | 1566695 | 19954.0 | 10 | 6 | 72 | 32 |
| one_shot_issue9 | 50 | 46 | 4 | 2.42 | 2.0 | 9 | 0 | 504315 | 6223.5 | 765480 | 12475.5 | 27 | 13 | 56 | 33 |
| issue17_rep1 | 50 | 50 | 0 | 5.32 | 4.0 | 18 | 0 | 565024 | 8480.0 | 1876023 | 24272.5 | 26 | 21 | 120 | 40 |
| issue17_rep2 | 50 | 50 | 0 | 4.52 | 4.0 | 16 | 0 | 408548 | 6439.0 | 1428551 | 21956.5 | 11 | 8 | 72 | 37 |
| issue17_rep3 | 50 | 50 | 0 | 4.48 | 4.0 | 18 | 0 | 373984 | 5634.5 | 1452925 | 21411.0 | 11 | 8 | 78 | 33 |
| issue17_rep4 | 50 | 50 | 0 | 4.12 | 4.0 | 10 | 0 | 363849 | 5782.5 | 1211568 | 21269.5 | 7 | 5 | 59 | 32 |
| issue17_rep5 | 50 | 50 | 0 | 4.42 | 4.0 | 11 | 0 | 383190 | 5885.5 | 1320387 | 22407.0 | 14 | 11 | 82 | 38 |

## 3. Agentic against one_shot, new version (mode_comparison/)
Outcome is `invasion/depth` or NO_ANSWER. `outcome_crosstab.csv` has one row per
pair of outcomes and counts patients. The first table below counts patients out of
the 66 annotated ones in the roster whose answer equals the annotation; no
answer counts as not agreeing. The second table is the same for the first 50
annotated patients alone (mode_comparison_first_50/), the set of the earlier result.
The patients added since are the difference between the two tables. `agentic_only` and `one_shot_only` are patients where only that mode
agrees; `mcnemar_exact_p` tests whether the two differ. These are single runs of
each mode on short single-document reports and one annotator, so this describes
the runs and does not show that one mode is better.

| field | annotated_patients | agentic_agrees | one_shot_agrees | agentic_only | one_shot_only | mcnemar_exact_p |
|---|---|---|---|---|---|---|
| invasion | 66 | 63 | 63 | 0 | 0 | 1.0 |
| depth | 66 | 53 | 53 | 1 | 1 | 1.0 |

First 50 annotated patients only:

| field | annotated_patients | agentic_agrees | one_shot_agrees | agentic_only | one_shot_only | mcnemar_exact_p |
|---|---|---|---|---|---|---|
| invasion | 50 | 47 | 47 | 0 | 0 | 1.0 |
| depth | 50 | 38 | 38 | 1 | 1 | 1.0 |

Patients whose outcome differs between the two modes:

| patient | agentic_outcome | one_shot_outcome | agentic_calls | one_shot_calls |
|---|---|---|---|---|
| TCGA-A5-A0GE | present/cannot_be_determined | present/less_than_50 | 11 | 1 |
| TCGA-A5-A0GR | present/fifty_or_greater | present/less_than_50 | 5 | 2 |
| TCGA-AW-A1PO | cannot_be_determined/not_applicable | cannot_be_determined/cannot_be_determined | 3 | 2 |
| TCGA-AX-A1C8 | NO_ANSWER | present/less_than_50 | 24 | 10 |
| TCGA-D1-A163 | present/less_than_50 | NO_ANSWER | 4 | 24 |
| TCGA-D1-A16Q | present/cannot_be_determined | present/less_than_50 | 4 | 1 |
| TCGA-DF-A2KU | cannot_be_determined/not_applicable | present/fifty_or_greater | 4 | 2 |
| TCGA-DF-A2KV | cannot_be_determined/not_applicable | present/fifty_or_greater | 4 | 3 |
| TCGA-DF-A2KZ | present/fifty_or_greater | cannot_be_determined/not_applicable | 5 | 1 |
| TCGA-DI-A0WH | NO_ANSWER | present/less_than_50 | 6 | 8 |
| TCGA-EY-A1G7 | present/less_than_50 | not_identified/not_applicable | 3 | 3 |
| TCGA-FI-A2EX | NO_ANSWER | present/less_than_50 | 24 | 2 |

## 4. The patients with no answer (mode_comparison/no_answer_patients.csv, no_answer_cases/)
`no_answer_cases/cases_across_runs.csv` follows the patients TCGA-AX-A1C8, TCGA-FI-A2EX, TCGA-DI-A0WH
across every run: outcome, calls, rejected submissions, most common rejection code,
cut-off replies, and OncoTrace's reason for having no answer.

| mode | patient | reason | calls | rejected_submissions | cut_off_replies |
|---|---|---|---|---|---|
| agentic | TCGA-AX-A1C8 | model_call_budget_exhausted | 24 | 29 | 1 |
| agentic | TCGA-DI-A0WH | truncated_without_tool_call | 6 | 1 | 3 |
| agentic | TCGA-FI-A2EX | model_call_budget_exhausted | 24 | 22 | 0 |
| one_shot | TCGA-D1-A163 | model_call_budget_exhausted | 24 | 24 | 1 |

`no_answer_cases/case_steps.csv` has one row per model call (tools asked for, reply
size, finish reason, rejection codes that followed). The summary below has one row
per patient and run. `calls_before_first_submit` counts calls that only looked at the
report; `cut_off_calls` are replies stopped by the token limit;
`longest_same_rejection_streak` is the longest run of rejections with the same reason
code in a row. No report text is in these tables.

| patient | run | calls | calls_before_first_submit | calls_with_submit | cut_off_calls | rejected_submissions | longest_same_rejection_streak | streak_reason | outcome |
|---|---|---|---|---|---|---|---|---|---|
| TCGA-AX-A1C8 | agentic_new | 24 | 3 | 20 | 1 | 29 | 16 | quantified_depth_not_classified | no answer |
| TCGA-AX-A1C8 | one_shot_new | 10 | 1 | 8 | 3 | 7 | 3 | citation_quote_not_found | answered |
| TCGA-AX-A1C8 | agentic_issue9 | 8 | 2 | 3 | 4 | 3 | 1 | citation_quote_ambiguous | no answer |
| TCGA-AX-A1C8 | one_shot_issue9 | 6 | 1 | 3 | 3 | 3 | 2 | citation_absent | no answer |
| TCGA-FI-A2EX | agentic_new | 24 | 2 | 22 | 0 | 22 | 21 | argument_not_a_list | no answer |
| TCGA-FI-A2EX | one_shot_new | 2 | 0 | 2 | 0 | 1 | 1 | quantified_depth_not_classified | answered |
| TCGA-FI-A2EX | agentic_issue9 | 4 | 2 | 2 | 0 | 1 | 1 | quantified_depth_not_classified | answered |
| TCGA-FI-A2EX | one_shot_issue9 | 24 | 0 | 24 | 1 | 38 | 23 | citation_quote_not_found | no answer |
| TCGA-DI-A0WH | agentic_new | 6 | 3 | 1 | 3 | 1 | 1 | citation_quote_ambiguous | no answer |
| TCGA-DI-A0WH | one_shot_new | 8 | 0 | 7 | 2 | 6 | 2 | citation_quote_ambiguous | answered |
| TCGA-DI-A0WH | agentic_issue9 | 7 | 2 | 2 | 4 | 2 | 1 | myometrial_invasion_percent_not_allowed | no answer |
| TCGA-DI-A0WH | one_shot_issue9 | 5 | 0 | 2 | 4 | 2 | 1 | evidence_citations_missing | no answer |

