### Scripts directory

This directory contains runnable Python scripts. Each script should use `argparse`, import its core functionality from `oncotrace_bench`, and be documented here and in the root README.md.

| Script | What it does |
|---|---|
| `check_provenance.py` | Checks `provenance.json` records: the clinic checkout was clean (or gave a `dirty_reason`), each recorded commit is on GitHub in its own repository, each run names one OncoTrace commit and one contract digest, agrees with its own run record, ran an unmodified package, is reachable by the group, and was not served by more than one server start. With no paths it checks the records your branch adds or changes; `make check-provenance ARGS=experiments` audits everything. Run it before opening a PR. |
