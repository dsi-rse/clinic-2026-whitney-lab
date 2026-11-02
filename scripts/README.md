### Scripts directory

This directory contains runnable Python scripts. Each script should use `argparse`, import its core functionality from `oncotrace_bench`, and be documented here and in the root README.md.

| Script | What it does |
|---|---|
| `check_provenance.py` | Checks every `provenance.json` under `experiments/` (or the paths given): the clinic checkout was clean, each recorded commit is on GitHub, each run names one OncoTrace commit and one contract digest, ran an unmodified package, is still there and group-readable, and did not span more than one server start. Run it with `make check-provenance` before opening a PR. |
