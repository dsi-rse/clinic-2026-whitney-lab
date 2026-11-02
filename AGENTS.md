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

## Experiment PR descriptions

This applies to experiment PRs: self-contained work that asks a question, runs something, and reports what happened. Annotation files, scaffolding, docs and bug fixes are exempt. See issue #33. It complements issue #31 (provenance) and issue #32 (reproducibility).

A reader who is not doing the runs should be able to say, from the text alone:
- what the question is;
- what was compared, and what single thing changed;
- how the authors would tell yes from no;
- what was found;
- how to read each table;
- what the main limits are.

### Three parts, visible at the top of the body, in this order
Detail goes below or in the README.

1. **Findings.** A one-sentence takeaway or two to five short bullets. Each is a plain claim with its number (for example, "49 of 50 patients got the same answer in all five runs"). Say what it means for the lab. Say if the result is inconclusive.
2. **What we did (the experimental design).** About ten lines in plain language:
   - the question, in one sentence, and why it matters;
   - what was run: on how many patients, and what was compared. Name the one thing that differs between the groups, and the baseline or control;
   - what result would count as yes and what as no, written before the runs where possible, with any pass bar;
   - the main limits (sample size, one annotator, and so on);
   - terms defined at first use (agentic, one_shot, contract, roster, temperature, and any label the tables use), or in a glossary;
   - no code identifiers, flags, commit hashes or file paths in this section. They belong in the README and `provenance.json`.
3. **Results.**
   - Before each table: one sentence on what a row is, what a column is, and what the numbers count ("patients out of 50").
   - Under each table: how to read it. Which numbers to compare, what a good value looks like, and the so-what in one sentence. Define every abbreviation and label.
   - Include the baseline or reference row (such as always guessing "present") so the numbers can be judged.
   - Every figure comes from a committed table (see "Reproducibility" above, item 2).

Then, collapsed or linked: the file table, how to run, checks, provenance and long tables. Don't repeat the README.

### Placement and length
- The three parts go at the top of the PR body, **outside any collapsed block**. Detail goes inside a collapsed `<details>` block below.
- This is an exception to the rule above that agent-written GitHub posts are collapsed. It applies to experiment PR bodies.
- Findings plus "What we did" should fit on about one screen, with the results tables after them.

### Template
- Open experiment PRs with `.github/PULL_REQUEST_TEMPLATE/experiment.md`. Add `?template=experiment.md` to the compare URL, or run `gh pr create --template .github/PULL_REQUEST_TEMPLATE/experiment.md`. GitHub does not fill in a named template on its own.
- Agents: do this for experiment PRs. Other PR types do not use this template.

### Who writes the description
It is fine to have an agent write the PR description (this may change later). But if a student is not capable of writing Findings and What we did in their own words, they likely do not understand the experiment. That is not good. Agents: do not take this learning opportunity away from the student. Ask the student to explain the question, the comparison and the yes/no bar first, and ask them to correct your draft.

## Local Preferences

If `agents.local.md` exists in the repo root, read it after this file.

`agents.local.md` is for personal preferences and durable student-specific guidance. It supplements the shared course rules above and should not be committed.

Students can copy `agents.local.example.md` to `agents.local.md` and customize it for their own checkout.
