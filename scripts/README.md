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
