# Evidence-buckets results: 2026-11-17_213637

Made 2026-11-18T03:36:37+00:00 by `experiments/evidence_buckets/compare_arms.py --run baseline_rep1=/Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs/2026-11-18_evidence_buckets_baseline/rep1 --run baseline_rep2=/Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs/2026-11-18_evidence_buckets_baseline/rep2 --run evidence_rep1=/Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs/2026-11-18_evidence_buckets_evidence/rep1 --run evidence_rep2=/Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs/2026-11-18_evidence_buckets_evidence/rep2`.

| | |
|---|---|
| Runs | baseline_rep1 `rep1` (66 records), baseline_rep2 `rep2` (66 records), evidence_rep1 `rep1` (66 records), evidence_rep2 `rep2` (66 records) |
| OncoTrace commit | `d4b7fd3` |
| Task contracts | `3d75c051`, `4e4fe0ea` |
| Clinic commit | `19925bd` |

The run folders were made on a laptop through OpenRouter and are not yet on the
shared cluster path; `provenance.json` records this as acknowledged. All numbers
are in `summary.txt`; the tables are the CSV files here. What each table holds
is in the experiment README.

## Findings

Superseded. This was the first analysis of the four runs, made with
`compare_arms.py` at the clinic commit above. That version had no
`pass_bar.csv`, so the pass-bar verdicts were not yet computed by code. The
next results folder adds that table; its other CSV files are byte-identical to
the ones here (checked with `cmp`). Read the findings in the experiment README
and the newer folder.
