This repo is for a student project in the Data Science Clinic. Students may use coding agents, but the course requirements place a strong emphasis on accessible, readable code that students can and do interact with manually. As a coding agent:
- Assume that you are speaking with a student unless specified otherwise.
- Prioritize being extremely clear and concise over using maximally efficient modern tools and following all software development best practices.
- Do not change code that the students have written without asking. They will have chosen approaches and frameworks that they are comfortable with, and moving away from their choices has a large cost: they may become unfamiliar with the codebase and unable to interact with it effectively.

Also note:
- There will be multiple students working in this repo, which may lead to divergence of structure and duplication of functionality. 

For Python development, follow these guidelines and encourage students to follow them:
- @docs/PYTHON_DEVELOPMENT_GUIDELINES.md

Other instructions:
- Do not change AGENTS.md unless explicitly asked to.
- Do not change PYTHON_DEVELOPMENT_GUIDELINES.md unless explicitly asked to.
- Do not change linting rules unless explcitly asked to.
- Sign your commits as Claude
- If you post on GitHub (issues, comments, etc), put your comment in a collapsed block like: <details><summary>Claude: {one-line summary of comment}</summary>{your comment}</details>

## Reproducibility

Experiment results must be reproducible by teammates and reviewers (see issue #32; provenance is covered in #31).

### 1. Everything a result depends on is readable by the team
- Put runs, edited inputs, and intermediate files under `/net/spaces/annawoodard/oncotrace/workspaces/<name>/` (or another shared path the mentor names), group-readable. Do not leave them in a home directory, `/tmp`, or personal scratch.
- Commit every script and config that produced a table, figure, or input in the PR. No private `analysis/` folders.
- If a file cannot be committed (protected report text, large runs), the README must say where it is, who can read it, and its SHA-256. Also commit the spec or script that regenerates it from the protected source.
- Before opening the PR, check access as someone else: ask a teammate or TA to `ls` and open the paths, or run `namei -l <path>`.

### 2. Every number comes from a table in the results folder
- Each figure in the PR body, README, or comments cites the file it comes from (e.g. `results/…/summary.csv`).
- Counts, percentages, "N of M" claims, and qualitative claims ("the same 11 patients in all runs") are computed by committed code. If something was checked by hand, say so, say how, and list the patient IDs.
- If a number changes, regenerate the tables and update the text. Don't edit one without the other.
- Prefer a generated results README (as `experiments/temperature/compare_temperature.py` writes) over typed tables.

### 3. A teammate can rerun the analysis from a fresh clone
- The README gives the exact commands, starting from `git clone`: required environment variables, `PYTHONPATH`, and Python dependencies, which must be declared in `pyproject.toml` or listed in the README.
- Scripts take paths as arguments. No `/home/<user>` or personal scratch paths as defaults.
- The README says which output should reproduce exactly (tables, CSVs) and how long the rerun takes.
- The reviewer's test: reading only the README, the analysis reruns in about 10 minutes without special access, and the output matches the committed tables.

### 4. Say what can't be rerun
- GPU/Slurm runs and model outputs can't be reproduced bit for bit. State that, keep the run folders, and make sure the analysis from those folders is rerunnable (item 3).
- Note where a run was resumed or split across servers or code versions.
- If the PR depends on another unmerged PR or branch, say which one. No results that can't be remade without it.

## Experiments and provenance

Every result folder must say what made it, so a reader months later can tell what produced the numbers and whether two results are comparable (see issue #31). Shared paths, sourced numbers, and rerunning from a fresh clone are covered by `## Reproducibility` above.

### 1. One helper
- Call `oncotrace_bench.provenance.build(inputs, runs, repo_root, ...)` and save the result as `provenance.json` next to the outputs. Don't write a second version of it: if a field is missing, add it to `build()`.
- Run `make check-provenance` before opening the PR. It checks items 2 and 3 below.

### 2. Record the run, not the machine you are analysing on
- Facts about a run (OncoTrace commit, contract digest, model, temperature, Slurm job) come from what OncoTrace wrote into the run folder. `run_state()` reads them. Never take them from `git rev-parse HEAD` of whatever checkout is open while you analyse: that was fixed days later and is a different thing.
- If your analysis imports code from a checkout (OncoTrace's `viewer/`, say), pass it as `analysis_repos=`. It is an input of the analysis, not the commit that made the run.

### 3. A clean, pushed commit
- Make results from a clean checkout: commit the code first, then the results. `clinic_repo.uncommitted_files` must be empty, or the results README must explain why not.
- Every recorded commit must exist on GitHub. A commit that is only in your checkout pins nothing.

### 4. A new timestamped results folder each time
- `results/<YYYY-MM-DD_HHMMSS>[_label]/`, holding the tables, a summary, `provenance.json`, and a README saying how to remake it.
- Never overwrite a results folder. Earlier attempts are evidence, including the ones that went wrong.

## Local Preferences

If `agents.local.md` exists in the repo root, read it after this file.

`agents.local.md` is for personal preferences and durable student-specific guidance. It supplements the shared course rules above and should not be committed.

Students can copy `agents.local.example.md` to `agents.local.md` and customize it for their own checkout.
