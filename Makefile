
# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# pipeline constants
# PROJECT_NAME
project_name := "oncotrace-bench"
project_dir := "$(current_abs_path)"

# environment variables
include .env

# Check required environment variables
ifeq ($(DATA_DIR),)
	$(error DATA_DIR must be set in .env file)
endif





open-ssh-login-node:
	code --remote ssh-remote+fe.ds ~/oncotrace-bench


# Run the endometrial failure-modes experiment on one OncoTrace run.
# Usage: make endometrial-failure-modes RUN=/path/to/run LABEL=baseline
# Each LABEL gets its own folder under experiments/endometrial_failure_modes/results/.
endometrial-failure-modes:
ifndef RUN
	$(error RUN must be set to an OncoTrace run folder)
endif
ifndef LABEL
	$(error LABEL must be set to a new name for this result set)
endif
	PYTHONPATH=src python experiments/endometrial_failure_modes/run_experiment.py --run $(RUN) --label $(LABEL)


# Run the evidence-following experiment (issue 8) on the original run and its arms.
# Usage: make evidence-following [LABEL=after-fix] [ARGS="--original <run> ..."]
# Each run gets a timestamped folder under experiments/evidence_following/results/.
evidence-following:
	PYTHONPATH=src python experiments/evidence_following/run_experiment.py $(if $(LABEL),--label $(LABEL)) $(ARGS)

# Compare the temperature 0 and 1.0 runs on the annotated patients.
# Usage: make temperature [LABEL=name] [ARGS="--run t0=<run> --run t1_r1=<run> ..."]
# Each run gets a timestamped folder under experiments/temperature/results/.
temperature:
	PYTHONPATH=src python experiments/temperature/compare_temperature.py $(if $(LABEL),--label $(LABEL)) $(ARGS)

# Build the annotation-only tables for the unresolved_conflicts investigation (issue 15).
# Usage: make unresolved-conflicts
unresolved-conflicts:
	PYTHONPATH=src python experiments/unresolved_conflicts/annotation_tables.py

# Compare the two issue 13 task contracts (B and C) on the original and edited reports.
# Usage: make issue13-contracts [LABEL=name] [ARGS="--runs-dir <folder> --date <YYYY-MM-DD>"]
# Each run gets a timestamped folder under experiments/evidence_following/results/.
issue13-contracts:
	PYTHONPATH=src python experiments/evidence_following/compare_contracts.py $(if $(LABEL),--label $(LABEL)) $(ARGS)
