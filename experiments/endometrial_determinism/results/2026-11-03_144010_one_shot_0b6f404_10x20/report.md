# Repeat-run stability: 2026-11-03_144010_one_shot_0b6f404_10x20

20 runs, 10 patients that every run finished (patients unfinished in some run are left out, not counted against it).

## What each run did

| run | patients | answered | no answer | calls | completion tokens | rejected submissions | cut-off replies | patients with a cut-off reply | share of tokens in cut-off replies |
|---|---|---|---|---|---|---|---|---|---|
| rep1 | 10 | 10 | 0 | 23 | 75492 | 12 | 3 | 2 | 0.326 |
| rep10 | 10 | 10 | 0 | 17 | 53719 | 8 | 1 | 1 | 0.152 |
| rep11 | 10 | 10 | 0 | 19 | 74132 | 6 | 5 | 3 | 0.553 |
| rep12 | 10 | 10 | 0 | 18 | 59063 | 7 | 3 | 3 | 0.416 |
| rep13 | 10 | 10 | 0 | 17 | 72657 | 6 | 4 | 3 | 0.451 |
| rep14 | 10 | 10 | 0 | 18 | 69969 | 6 | 3 | 2 | 0.351 |
| rep15 | 10 | 10 | 0 | 18 | 73459 | 6 | 3 | 2 | 0.335 |
| rep16 | 10 | 10 | 0 | 16 | 64757 | 11 | 4 | 3 | 0.506 |
| rep17 | 10 | 10 | 0 | 22 | 77040 | 11 | 5 | 4 | 0.532 |
| rep18 | 10 | 10 | 0 | 20 | 81537 | 18 | 3 | 1 | 0.301 |
| rep19 | 10 | 9 | 1 | 42 | 83132 | 33 | 2 | 2 | 0.197 |
| rep2 | 10 | 10 | 0 | 19 | 57035 | 8 | 2 | 2 | 0.287 |
| rep20 | 10 | 10 | 0 | 23 | 79197 | 11 | 5 | 4 | 0.517 |
| rep3 | 10 | 10 | 0 | 20 | 72681 | 12 | 4 | 3 | 0.451 |
| rep4 | 10 | 10 | 0 | 17 | 66433 | 15 | 4 | 3 | 0.493 |
| rep5 | 10 | 10 | 0 | 19 | 46723 | 7 | 2 | 2 | 0.351 |
| rep6 | 10 | 10 | 0 | 19 | 66249 | 10 | 2 | 1 | 0.247 |
| rep7 | 10 | 10 | 0 | 22 | 79245 | 11 | 3 | 3 | 0.31 |
| rep8 | 10 | 10 | 0 | 20 | 60533 | 9 | 3 | 2 | 0.406 |
| rep9 | 10 | 10 | 0 | 20 | 61388 | 9 | 1 | 1 | 0.133 |

A cut-off reply is one the server stopped at the reply token cap (finish reason `length`).

## Patients with the same outcome in every run: 8 of 10 (unstable: 2, 20%)

An outcome is the invasion and depth answer, or no answer. See `unstable_patients.csv` for who changed and how.

## How much cost varies for the same patient

| measure | identical in every run | mean SD per patient | largest range |
|---|---|---|---|
| model calls | 0 / 10 | 1.1 | 23 |
| completion tokens | 0 / 10 | 2907.2 | 18638 |
| rejected submissions | 0 / 10 | 1.4 | 24 |

## Where the runs first differ

| reply | identical in every run |
|---|---|
| first reply (usually a short tool call) | 0 / 10 |
| first long reasoning reply (over 1000 tokens) | 0 / 10 |

## Agreement between pairs of runs

| run a | run b | same outcome |
|---|---|---|
| rep1 | rep10 | 10 / 10 |
| rep1 | rep11 | 10 / 10 |
| rep1 | rep12 | 10 / 10 |
| rep1 | rep13 | 10 / 10 |
| rep1 | rep14 | 10 / 10 |
| rep1 | rep15 | 10 / 10 |
| rep1 | rep16 | 10 / 10 |
| rep1 | rep17 | 9 / 10 |
| rep1 | rep18 | 10 / 10 |
| rep1 | rep19 | 9 / 10 |
| rep1 | rep2 | 10 / 10 |
| rep1 | rep20 | 10 / 10 |
| rep1 | rep3 | 10 / 10 |
| rep1 | rep4 | 10 / 10 |
| rep1 | rep5 | 9 / 10 |
| rep1 | rep6 | 10 / 10 |
| rep1 | rep7 | 9 / 10 |
| rep1 | rep8 | 10 / 10 |
| rep1 | rep9 | 10 / 10 |
| rep10 | rep11 | 10 / 10 |
| rep10 | rep12 | 10 / 10 |
| rep10 | rep13 | 10 / 10 |
| rep10 | rep14 | 10 / 10 |
| rep10 | rep15 | 10 / 10 |
| rep10 | rep16 | 10 / 10 |
| rep10 | rep17 | 9 / 10 |
| rep10 | rep18 | 10 / 10 |
| rep10 | rep19 | 9 / 10 |
| rep10 | rep2 | 10 / 10 |
| rep10 | rep20 | 10 / 10 |
| rep10 | rep3 | 10 / 10 |
| rep10 | rep4 | 10 / 10 |
| rep10 | rep5 | 9 / 10 |
| rep10 | rep6 | 10 / 10 |
| rep10 | rep7 | 9 / 10 |
| rep10 | rep8 | 10 / 10 |
| rep10 | rep9 | 10 / 10 |
| rep11 | rep12 | 10 / 10 |
| rep11 | rep13 | 10 / 10 |
| rep11 | rep14 | 10 / 10 |
| rep11 | rep15 | 10 / 10 |
| rep11 | rep16 | 10 / 10 |
| rep11 | rep17 | 9 / 10 |
| rep11 | rep18 | 10 / 10 |
| rep11 | rep19 | 9 / 10 |
| rep11 | rep2 | 10 / 10 |
| rep11 | rep20 | 10 / 10 |
| rep11 | rep3 | 10 / 10 |
| rep11 | rep4 | 10 / 10 |
| rep11 | rep5 | 9 / 10 |
| rep11 | rep6 | 10 / 10 |
| rep11 | rep7 | 9 / 10 |
| rep11 | rep8 | 10 / 10 |
| rep11 | rep9 | 10 / 10 |
| rep12 | rep13 | 10 / 10 |
| rep12 | rep14 | 10 / 10 |
| rep12 | rep15 | 10 / 10 |
| rep12 | rep16 | 10 / 10 |
| rep12 | rep17 | 9 / 10 |
| rep12 | rep18 | 10 / 10 |
| rep12 | rep19 | 9 / 10 |
| rep12 | rep2 | 10 / 10 |
| rep12 | rep20 | 10 / 10 |
| rep12 | rep3 | 10 / 10 |
| rep12 | rep4 | 10 / 10 |
| rep12 | rep5 | 9 / 10 |
| rep12 | rep6 | 10 / 10 |
| rep12 | rep7 | 9 / 10 |
| rep12 | rep8 | 10 / 10 |
| rep12 | rep9 | 10 / 10 |
| rep13 | rep14 | 10 / 10 |
| rep13 | rep15 | 10 / 10 |
| rep13 | rep16 | 10 / 10 |
| rep13 | rep17 | 9 / 10 |
| rep13 | rep18 | 10 / 10 |
| rep13 | rep19 | 9 / 10 |
| rep13 | rep2 | 10 / 10 |
| rep13 | rep20 | 10 / 10 |
| rep13 | rep3 | 10 / 10 |
| rep13 | rep4 | 10 / 10 |
| rep13 | rep5 | 9 / 10 |
| rep13 | rep6 | 10 / 10 |
| rep13 | rep7 | 9 / 10 |
| rep13 | rep8 | 10 / 10 |
| rep13 | rep9 | 10 / 10 |
| rep14 | rep15 | 10 / 10 |
| rep14 | rep16 | 10 / 10 |
| rep14 | rep17 | 9 / 10 |
| rep14 | rep18 | 10 / 10 |
| rep14 | rep19 | 9 / 10 |
| rep14 | rep2 | 10 / 10 |
| rep14 | rep20 | 10 / 10 |
| rep14 | rep3 | 10 / 10 |
| rep14 | rep4 | 10 / 10 |
| rep14 | rep5 | 9 / 10 |
| rep14 | rep6 | 10 / 10 |
| rep14 | rep7 | 9 / 10 |
| rep14 | rep8 | 10 / 10 |
| rep14 | rep9 | 10 / 10 |
| rep15 | rep16 | 10 / 10 |
| rep15 | rep17 | 9 / 10 |
| rep15 | rep18 | 10 / 10 |
| rep15 | rep19 | 9 / 10 |
| rep15 | rep2 | 10 / 10 |
| rep15 | rep20 | 10 / 10 |
| rep15 | rep3 | 10 / 10 |
| rep15 | rep4 | 10 / 10 |
| rep15 | rep5 | 9 / 10 |
| rep15 | rep6 | 10 / 10 |
| rep15 | rep7 | 9 / 10 |
| rep15 | rep8 | 10 / 10 |
| rep15 | rep9 | 10 / 10 |
| rep16 | rep17 | 9 / 10 |
| rep16 | rep18 | 10 / 10 |
| rep16 | rep19 | 9 / 10 |
| rep16 | rep2 | 10 / 10 |
| rep16 | rep20 | 10 / 10 |
| rep16 | rep3 | 10 / 10 |
| rep16 | rep4 | 10 / 10 |
| rep16 | rep5 | 9 / 10 |
| rep16 | rep6 | 10 / 10 |
| rep16 | rep7 | 9 / 10 |
| rep16 | rep8 | 10 / 10 |
| rep16 | rep9 | 10 / 10 |
| rep17 | rep18 | 9 / 10 |
| rep17 | rep19 | 8 / 10 |
| rep17 | rep2 | 9 / 10 |
| rep17 | rep20 | 9 / 10 |
| rep17 | rep3 | 9 / 10 |
| rep17 | rep4 | 9 / 10 |
| rep17 | rep5 | 10 / 10 |
| rep17 | rep6 | 9 / 10 |
| rep17 | rep7 | 10 / 10 |
| rep17 | rep8 | 9 / 10 |
| rep17 | rep9 | 9 / 10 |
| rep18 | rep19 | 9 / 10 |
| rep18 | rep2 | 10 / 10 |
| rep18 | rep20 | 10 / 10 |
| rep18 | rep3 | 10 / 10 |
| rep18 | rep4 | 10 / 10 |
| rep18 | rep5 | 9 / 10 |
| rep18 | rep6 | 10 / 10 |
| rep18 | rep7 | 9 / 10 |
| rep18 | rep8 | 10 / 10 |
| rep18 | rep9 | 10 / 10 |
| rep19 | rep2 | 9 / 10 |
| rep19 | rep20 | 9 / 10 |
| rep19 | rep3 | 9 / 10 |
| rep19 | rep4 | 9 / 10 |
| rep19 | rep5 | 8 / 10 |
| rep19 | rep6 | 9 / 10 |
| rep19 | rep7 | 8 / 10 |
| rep19 | rep8 | 9 / 10 |
| rep19 | rep9 | 9 / 10 |
| rep2 | rep20 | 10 / 10 |
| rep2 | rep3 | 10 / 10 |
| rep2 | rep4 | 10 / 10 |
| rep2 | rep5 | 9 / 10 |
| rep2 | rep6 | 10 / 10 |
| rep2 | rep7 | 9 / 10 |
| rep2 | rep8 | 10 / 10 |
| rep2 | rep9 | 10 / 10 |
| rep20 | rep3 | 10 / 10 |
| rep20 | rep4 | 10 / 10 |
| rep20 | rep5 | 9 / 10 |
| rep20 | rep6 | 10 / 10 |
| rep20 | rep7 | 9 / 10 |
| rep20 | rep8 | 10 / 10 |
| rep20 | rep9 | 10 / 10 |
| rep3 | rep4 | 10 / 10 |
| rep3 | rep5 | 9 / 10 |
| rep3 | rep6 | 10 / 10 |
| rep3 | rep7 | 9 / 10 |
| rep3 | rep8 | 10 / 10 |
| rep3 | rep9 | 10 / 10 |
| rep4 | rep5 | 9 / 10 |
| rep4 | rep6 | 10 / 10 |
| rep4 | rep7 | 9 / 10 |
| rep4 | rep8 | 10 / 10 |
| rep4 | rep9 | 10 / 10 |
| rep5 | rep6 | 9 / 10 |
| rep5 | rep7 | 10 / 10 |
| rep5 | rep8 | 9 / 10 |
| rep5 | rep9 | 9 / 10 |
| rep6 | rep7 | 9 / 10 |
| rep6 | rep8 | 10 / 10 |
| rep6 | rep9 | 10 / 10 |
| rep7 | rep8 | 9 / 10 |
| rep7 | rep9 | 9 / 10 |
| rep8 | rep9 | 10 / 10 |

## Agreement with the human annotations

| field | run | annotated patients | correct | wrong | over_committed | abstained |
|---|---|---|---|---|---|---|
| invasion | rep1 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep10 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep11 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep12 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep13 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep14 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep15 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep16 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep17 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep18 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep19 | 10 | 9 | 0 | 0 | 1 |
| invasion | rep2 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep20 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep3 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep4 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep5 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep6 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep7 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep8 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep9 | 10 | 10 | 0 | 0 | 0 |
| depth | rep1 | 10 | 9 | 0 | 1 | 0 |
| depth | rep10 | 10 | 9 | 0 | 1 | 0 |
| depth | rep11 | 10 | 9 | 0 | 1 | 0 |
| depth | rep12 | 10 | 9 | 0 | 1 | 0 |
| depth | rep13 | 10 | 9 | 0 | 1 | 0 |
| depth | rep14 | 10 | 9 | 0 | 1 | 0 |
| depth | rep15 | 10 | 9 | 0 | 1 | 0 |
| depth | rep16 | 10 | 9 | 0 | 1 | 0 |
| depth | rep17 | 10 | 8 | 1 | 1 | 0 |
| depth | rep18 | 10 | 9 | 0 | 1 | 0 |
| depth | rep19 | 10 | 8 | 0 | 1 | 1 |
| depth | rep2 | 10 | 9 | 0 | 1 | 0 |
| depth | rep20 | 10 | 9 | 0 | 1 | 0 |
| depth | rep3 | 10 | 9 | 0 | 1 | 0 |
| depth | rep4 | 10 | 9 | 0 | 1 | 0 |
| depth | rep5 | 10 | 8 | 1 | 1 | 0 |
| depth | rep6 | 10 | 9 | 0 | 1 | 0 |
| depth | rep7 | 10 | 8 | 1 | 1 | 0 |
| depth | rep8 | 10 | 9 | 0 | 1 | 0 |
| depth | rep9 | 10 | 9 | 0 | 1 | 0 |
