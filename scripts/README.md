### Scripts directory

This directory contains runnable Python scripts. Each script should use `argparse`, import its core functionality from `oncotrace_bench`, and be documented here and in the root README.md.

#### `outcome_table.py`

Counts every roster patient in a run as an accepted answer, no accepted
submission, server error, or unfinished (no record), then breaks accepted
answers down by invasion and by depth value (including `cannot_be_determined`).
Reading of the run is done by TraceView, so `--oncotrace` must point at an
OncoTrace clone (default `~/oncotrace`).

```bash
PYTHONPATH=src python scripts/outcome_table.py \
  --run /path/to/run --task tasks/endo_myometrial_invasion.yaml \
  --roster /path/to/roster_ucec.csv [--out-dir tables/]
```

#### `inspect_patients.py`

Prints a text-free summary of what OncoTrace did for chosen patients: the step
sequence, read ranges against document length, refusal signatures, truncated
replies, and the last event. Reading is done by TraceView.

```bash
PYTHONPATH=src python scripts/inspect_patients.py \
  --run /path/to/run --task tasks/endo_myometrial_invasion.yaml \
  --units TCGA-A5-A0GP TCGA-A5-A0GE
```

#### `confidence_table.py`

Matches the run's patients to the human annotations by ID and counts agreement
by the model's confidence (high, medium, low), plus patients with no answer.
Uses TraceView's `score_run` and `agreement_by_confidence` (from the OncoTrace
clone's `viewer/scoring.py`, via `--oncotrace`).

```bash
PYTHONPATH=src python scripts/confidence_table.py \
  --run /path/to/run --task tasks/endo_myometrial_invasion.yaml
```

#### `find_patients.py`

Lists patients to open in TraceView, filtered by what happened to them. Fills
two gaps in TraceView's filters: patients with a reply cut off at the token cap
(answered or not), and refusals grouped by signature. Filters combine with AND.

```bash
# which refusals happened, how many patients each affected, and how many recovered
PYTHONPATH=src python scripts/find_patients.py --run RUN --task TASK --summary
# unanswered patients stopped by the call budget
PYTHONPATH=src python scripts/find_patients.py --run RUN --task TASK --no-answer \
  --reason model_call_budget_exhausted
# answered patients with a cut-off reply, or anyone refused with one signature
PYTHONPATH=src python scripts/find_patients.py --run RUN --task TASK --answered --cut-off
PYTHONPATH=src python scripts/find_patients.py --run RUN --task TASK \
  --refused-with citation_quote_not_found
```

Open a listed patient by choosing it in TraceView's Units tab. `--out file.csv`
saves the table.
