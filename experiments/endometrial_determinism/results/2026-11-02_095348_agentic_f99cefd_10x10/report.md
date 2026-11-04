# Repeat-run stability: 2026-11-02_095348_agentic_f99cefd_10x10

10 runs, 10 patients that every run finished (patients unfinished in some run are left out, not counted against it).

## What each run did

| run | patients | answered | no answer | calls | completion tokens | rejected submissions | cut-off replies | patients with a cut-off reply | share of tokens in cut-off replies |
|---|---|---|---|---|---|---|---|---|---|
| rep1 | 10 | 10 | 0 | 37 | 54385 | 6 | 1 | 1 | 0.151 |
| rep10 | 10 | 10 | 0 | 39 | 58846 | 9 | 1 | 1 | 0.139 |
| rep2 | 10 | 10 | 0 | 40 | 84960 | 9 | 5 | 2 | 0.482 |
| rep3 | 10 | 10 | 0 | 42 | 63420 | 10 | 2 | 1 | 0.258 |
| rep4 | 10 | 10 | 0 | 38 | 61458 | 6 | 1 | 1 | 0.133 |
| rep5 | 10 | 10 | 0 | 49 | 116513 | 26 | 7 | 3 | 0.492 |
| rep6 | 10 | 10 | 0 | 41 | 70342 | 8 | 3 | 2 | 0.349 |
| rep7 | 10 | 10 | 0 | 44 | 71213 | 11 | 3 | 3 | 0.345 |
| rep8 | 10 | 10 | 0 | 41 | 90811 | 8 | 6 | 3 | 0.541 |
| rep9 | 10 | 10 | 0 | 41 | 68203 | 10 | 3 | 3 | 0.36 |

A cut-off reply is one the server stopped at the reply token cap (finish reason `length`).

## Patients with the same outcome in every run: 9 of 10 (unstable: 1, 10%)

An outcome is the invasion and depth answer, or no answer. See `unstable_patients.csv` for who changed and how.

## How much cost varies for the same patient

| measure | identical in every run | mean SD per patient | largest range |
|---|---|---|---|
| model calls | 0 / 10 | 0.7 | 8 |
| completion tokens | 0 / 10 | 3217.0 | 32199 |
| rejected submissions | 1 / 10 | 0.9 | 17 |

## Where the runs first differ

| reply | identical in every run |
|---|---|
| first reply (usually a short tool call) | 1 / 10 |
| first long reasoning reply (over 1000 tokens) | 0 / 10 |

## Agreement between pairs of runs

| run a | run b | same outcome |
|---|---|---|
| rep1 | rep10 | 10 / 10 |
| rep1 | rep2 | 10 / 10 |
| rep1 | rep3 | 10 / 10 |
| rep1 | rep4 | 10 / 10 |
| rep1 | rep5 | 9 / 10 |
| rep1 | rep6 | 9 / 10 |
| rep1 | rep7 | 9 / 10 |
| rep1 | rep8 | 10 / 10 |
| rep1 | rep9 | 10 / 10 |
| rep10 | rep2 | 10 / 10 |
| rep10 | rep3 | 10 / 10 |
| rep10 | rep4 | 10 / 10 |
| rep10 | rep5 | 9 / 10 |
| rep10 | rep6 | 9 / 10 |
| rep10 | rep7 | 9 / 10 |
| rep10 | rep8 | 10 / 10 |
| rep10 | rep9 | 10 / 10 |
| rep2 | rep3 | 10 / 10 |
| rep2 | rep4 | 10 / 10 |
| rep2 | rep5 | 9 / 10 |
| rep2 | rep6 | 9 / 10 |
| rep2 | rep7 | 9 / 10 |
| rep2 | rep8 | 10 / 10 |
| rep2 | rep9 | 10 / 10 |
| rep3 | rep4 | 10 / 10 |
| rep3 | rep5 | 9 / 10 |
| rep3 | rep6 | 9 / 10 |
| rep3 | rep7 | 9 / 10 |
| rep3 | rep8 | 10 / 10 |
| rep3 | rep9 | 10 / 10 |
| rep4 | rep5 | 9 / 10 |
| rep4 | rep6 | 9 / 10 |
| rep4 | rep7 | 9 / 10 |
| rep4 | rep8 | 10 / 10 |
| rep4 | rep9 | 10 / 10 |
| rep5 | rep6 | 9 / 10 |
| rep5 | rep7 | 10 / 10 |
| rep5 | rep8 | 9 / 10 |
| rep5 | rep9 | 9 / 10 |
| rep6 | rep7 | 9 / 10 |
| rep6 | rep8 | 9 / 10 |
| rep6 | rep9 | 9 / 10 |
| rep7 | rep8 | 9 / 10 |
| rep7 | rep9 | 9 / 10 |
| rep8 | rep9 | 10 / 10 |

## Agreement with the human annotations

| field | run | annotated patients | correct | wrong | over_committed | abstained |
|---|---|---|---|---|---|---|
| invasion | rep1 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep10 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep2 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep3 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep4 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep5 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep6 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep7 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep8 | 10 | 10 | 0 | 0 | 0 |
| invasion | rep9 | 10 | 10 | 0 | 0 | 0 |
| depth | rep1 | 10 | 9 | 0 | 1 | 0 |
| depth | rep10 | 10 | 9 | 0 | 1 | 0 |
| depth | rep2 | 10 | 9 | 0 | 1 | 0 |
| depth | rep3 | 10 | 9 | 0 | 1 | 0 |
| depth | rep4 | 10 | 9 | 0 | 1 | 0 |
| depth | rep5 | 10 | 8 | 1 | 1 | 0 |
| depth | rep6 | 10 | 8 | 1 | 1 | 0 |
| depth | rep7 | 10 | 8 | 1 | 1 | 0 |
| depth | rep8 | 10 | 9 | 0 | 1 | 0 |
| depth | rep9 | 10 | 9 | 0 | 1 | 0 |
