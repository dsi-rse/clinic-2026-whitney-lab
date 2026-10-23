
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



# Run the evidence-following experiment (issue 8) on the original run and its arms.
# Usage: make evidence-following [LABEL=after-fix] [ARGS="--original <run> ..."]
# Each run gets a timestamped folder under experiments/evidence_following/results/.
evidence-following:
	PYTHONPATH=src python experiments/evidence_following/run_experiment.py $(if $(LABEL),--label $(LABEL)) $(ARGS)

# Build the annotation-only tables for the unresolved_conflicts investigation (issue 15).
# Usage: make unresolved-conflicts
unresolved-conflicts:
	PYTHONPATH=src python experiments/unresolved_conflicts/annotation_tables.py
