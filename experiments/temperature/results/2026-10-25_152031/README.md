# Temperature results: 2026-10-25_152031

Made 2026-10-25T20:20:42+00:00 by `experiments/temperature/compare_temperature.py`.

| | |
|---|---|
| Runs | t0 `2026-10-23_temperature_t0` (50 records, temperature 0.0), t1_r1 `2026-10-23_temperature_t1_r1` (50 records, temperature 1.0), t1_r2 `2026-10-23_temperature_t1_r2` (50 records, temperature 1.0), t1_r3 `2026-10-23_temperature_t1_r3` (50 records, temperature 1.0) |
| OncoTrace commit | `fc3dadc` |
| Task contract | `ba27b6ce` |
| Clinic commit | `bc02dc9` |

All numbers are in `summary.txt`; the tables are the CSV files here. What each
file holds is in the experiment README.

## Findings

Four runs on the 50 annotated patients, one server start (job 2236218): T0
(0.0 / 1.0) once, T1 (1.0 / 0.95) three times.

- **Accuracy did not change.** Invasion agreed with the annotations in 47/50
  in all four runs, and depth in 38/50 (37 in T1 r1). The only answer change in
  200 patient-runs is TCGA-A5-A0GR: depth `fifty_or_greater` in T1 r1 instead
  of `less_than_50`, which is wrong. Its confidence was `medium` at T0.
- **Confidence did not change.** It was `high` in 47/50 (T0) and 46, 48 and 49
  (T1).
- **T1 does more work.** The median stays at 4 calls. The mean goes from 4.1 to
  4.7–5.2, the maximum from 11 to 15–22, and patients with 8 or more calls from
  1 to 5–8. Per patient, 30/50 used more calls on average at T1 and 13 fewer.
  Tokens rose for 36/50, median ratio 1.21. Tokens per call rose from 1692 to
  2084–2217.
- **Over-commitment is not a sampling effect.** Every other disagreement is the
  same in all four runs. That includes the 11 #13 patients whose depth is
  annotated `cannot_be_determined`. No run answered `cannot_be_determined` for
  depth.
- **No `no_answer` in any run.** Runs before dsi-rse/oncotrace#6 had 1–9 of these
  50. That is a different contract, so this is not a controlled comparison.

**So what:** keep temperature 0. T1 costs more and changes nothing measurable
here. Repeats at T1 do not flag the ambiguous patients.

**Limits:** 50 patients, one annotator, 45 from one site, one server start, and a
single T0 run. One answer change is too few to compare stability between the
two settings.
