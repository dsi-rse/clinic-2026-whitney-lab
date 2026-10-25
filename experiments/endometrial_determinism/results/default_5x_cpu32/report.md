# Repeat-run stability: default_5x_cpu32

5 runs, 50 patients that every run finished (patients unfinished in some run are left out, not counted against it).

## What each run did

| run | patients | answered | no answer | calls | completion tokens | rejected submissions |
|---|---|---|---|---|---|---|
| rep1 | 50 | 50 | 0 | 266 | 565024 | 120 |
| rep2 | 50 | 50 | 0 | 226 | 408548 | 72 |
| rep3 | 50 | 50 | 0 | 224 | 373984 | 78 |
| rep4 | 50 | 50 | 0 | 206 | 363849 | 59 |
| rep5 | 50 | 50 | 0 | 221 | 383190 | 82 |

## Patients with the same outcome in every run: 49 of 50 (unstable: 1, 2%)

An outcome is the invasion and depth answer, or no answer. See `unstable_patients.csv` for who changed and how.

## How much cost varies for the same patient

| measure | identical in every run | mean SD per patient | largest range |
|---|---|---|---|
| model calls | 6 / 50 | 1.3 | 15 |
| completion tokens | 0 / 50 | 4138.3 | 50831 |
| rejected submissions | 7 / 50 | 1.5 | 14 |

## Where the runs first differ

| reply | identical in every run |
|---|---|
| first reply (usually a short tool call) | 20 / 50 |
| first long reasoning reply (over 1000 tokens) | 0 / 50 |

## Agreement between pairs of runs

| run a | run b | same outcome |
|---|---|---|
| rep1 | rep2 | 49 / 50 |
| rep1 | rep3 | 50 / 50 |
| rep1 | rep4 | 50 / 50 |
| rep1 | rep5 | 50 / 50 |
| rep2 | rep3 | 49 / 50 |
| rep2 | rep4 | 49 / 50 |
| rep2 | rep5 | 49 / 50 |
| rep3 | rep4 | 50 / 50 |
| rep3 | rep5 | 50 / 50 |
| rep4 | rep5 | 50 / 50 |

## Agreement with the human annotations

| field | run | annotated patients | correct | wrong | over_committed | abstained |
|---|---|---|---|---|---|---|
| invasion | rep1 | 50 | 47 | 0 | 3 | 0 |
| invasion | rep2 | 50 | 47 | 0 | 3 | 0 |
| invasion | rep3 | 50 | 47 | 0 | 3 | 0 |
| invasion | rep4 | 50 | 47 | 0 | 3 | 0 |
| invasion | rep5 | 50 | 47 | 0 | 3 | 0 |
| depth | rep1 | 50 | 38 | 0 | 12 | 0 |
| depth | rep2 | 50 | 37 | 1 | 12 | 0 |
| depth | rep3 | 50 | 38 | 0 | 12 | 0 |
| depth | rep4 | 50 | 38 | 0 | 12 | 0 |
| depth | rep5 | 50 | 38 | 0 | 12 | 0 |
