# The Whitney lab PR checklist

One verdict per item: **pass**, **fail**, **decide** (a mentor call, not the author's fault),
**could not verify**, or **n/a**, with one line of evidence (command outcome, file and line).
This repo is a laboratory: the insights are the product and the code is secondary, though it must
reproduce. Items 9 to 15 (the task, the design, the numbers, provenance, the body) matter most;
items 3 to 7 (code quality) matter only where they affect a result or a rerun.

Items are about what **this PR changes**. An old problem elsewhere is a suggestion at most. Mark
**fail** only for things that matter (a wrong or unsourced number, an unrunnable analysis, an
unreadable path, a misleading claim). Minor wording, style or tidiness is a **pass**, or left out. Where
`AGENTS.md` is stricter, it wins; name the rule. Tests are not required in this lab (see item 5).

---

## Code

### 1. Runs from a fresh clone

Follow the README in a fresh clone (venv or cluster). Every dependency is declared, including
packages imported through an OncoTrace checkout.

- **Fail:** a README step that is missing or wrong, an undeclared dependency (`ModuleNotFoundError`),
  or a hard-coded personal path (`/home/<user>`, personal scratch).
- Docker: only check if the repo has a Dockerfile. No Docker here is **could not verify**.

### 2. Notebooks (if any)

Run in README order, no `!pip install`, functions in modules, names that say what they show.
Usually **n/a**.

### 3. Documented, clear purpose

New functions have docstrings, files and functions are named for what they do, the README says how to
run anything new and explains new non-code files, and scripts don't run at import (`__main__` guard).

### 4. No dead code

Commented-out blocks, unused functions or files (search for callers first), leftover debugging, and
errors silenced with `except: pass`.

### 5. Decision and scoring rules are correct

Tests are optional here. But any function that decides a headline number (a pass bar, an "honest" or
"correct" rule, a metric) must be right. Read it branch by branch and check its output against the
committed rows.

- **Fail:** a rule that scores wrongly, or silently loosens its own criterion.
- **Note:** latent gaps that don't change today's numbers.
- A missing test is at most an optional suggestion.

### 6. Ruff and shortcuts

`ruff check` and `ruff format --check` pass at the repo's pinned version.

- **Fail:** blanket `# noqa`, a rule ignored repo-wide, or no stated reason for a new ignore.
- Report every new `noqa`, lint change, removed pre-commit hook, and deleted or weakened test.
  A narrow ignore with a reason that holds is a pass.

### 7. `AGENTS.md` followed

Check the diff against each rule. **Always flag** edits to `AGENTS.md`, `CLAUDE.md` or similar.
Agent-written posts (PR bodies, issues) should be collapsed `<details><summary>Claude: …`; review
comments are the exception (uncollapsed). No `AGENTS.md`: n/a.

---

## Direction

### 8. Issue link and PR status

- `closingIssuesReferences` matches the intent. Read the body too. GitHub matches closing
  keywords in any sentence ("doesn't close #20" still closes), and "Refs #N" can still link.
- **Fail:** the link and the body disagree, a partial step closes its issue, or the issue isn't
  linked when it should be.
- `isDraft` matches how the PR describes itself ("draft" in the title but not a draft is a finding).
- Leftover placeholders (`<!-- … -->`), a stale body (claims files or numbers not in the diff), and
  no one-sentence takeaway at the top.

### 9. Solves the task

Go through the issue's acceptance criteria and mark each **met**, **partly met**, **not met**, citing
the file. **Fail:** a criterion not met and not explained. A stated partial step is a **pass with a
note**. Note large unrequested changes. No checkable criteria: **could not verify**.

### 10. Coherent with the repo

Compare with `main`. The lab pattern is `experiments/<name>/` with a README, shared helpers
(`oncotrace_bench.records`, `oncotrace_bench.provenance`), a `make` target, and a timestamped
`results/` folder with generated tables.

- **Fail:** the PR duplicates a shared helper or breaks an established pattern.
- **Decide:** two open PRs set conflicting standards where `main` has none.

---

## Experiments and results

Only for PRs that report numbers. Otherwise n/a.

### 11. Experiment design

- One factor changed at a time, with matched controls.
- Expected answers or pass bars written **before** the runs (and whether git can show the order).
- Small-n and single-annotator caveats stated (e.g. 50 patients, 45 `present`).
- Same patients and code version across compared arms.
- No dependence on another unmerged PR.
- A pass bar or clinical convention the author invented is **decide**, not fail.

### 12. Numbers are sourced and rerunnable

- **Number audit:** list every figure in the PR text and README and map it to a committed table or
  script. **Fail:** a number with no source, or one that disagrees with the committed table.
- **Rerun:** run the analysis and diff against the committed tables (byte for byte; CRLF aside).
  **Fail:** a difference.
- **Access:** you can read every path the results depend on. **Fail:** files in a private
  workspace, a home directory or personal scratch.
- Randomness and LLM nondeterminism are stated; GPU and Slurm runs are **could not verify**, and the
  PR should say so.

### 13. No leakage

Test information reaching training, tuning on the evaluation set, or duplicate patients across
splits. Usually **n/a** for lab experiments, but check anything that picks a setting using the
annotated set it then reports on.

---

## Provenance

### 14. Provenance is recorded and checkable

- Uses `oncotrace_bench.provenance.build` and writes `provenance.json` next to the results.
- Records the **run**, not the analysis machine: OncoTrace commit and contract digest, `package_modified`
  false, config hash, model, and job IDs.
- `uncommitted_files` is empty or explained, and every recorded commit **exists on GitHub**
  (`gh api repos/<owner>/<repo>/commits/<sha>`).
- Timestamped results folder; raw data and run folders are not modified.
- **Fail:** no provenance record, an unpinned or missing commit, or code that changes raw data.

---

## PR description

### 15. The body is readable by an outsider (experiment PRs only)

Experiment PRs only; everything else is **n/a**. Check against `references/pr-body.md` and the reader
test, and name what is missing.

- **Findings:** a takeaway or short bullets, visible at the top, in plain words with numbers.
- **Design:** a plain-language "what we did": the question, what was compared and the one thing that
  changed, what would count as an answer, and the limits. Terms defined at first use, and no
  identifiers or hashes in the prose.
- **Results:** every table has a sentence on what rows and columns are and what to compare, a
  definition of each label or abbreviation, and a one-line so-what. A baseline row where one helps.
- **Focus:** file lists, commands, checks and provenance sit below or in the README, not in the way.
- **Fail:** no design section, any table without a reading guide, or an outsider who can't answer
  reader-test questions 1 to 3 or 5. Undefined jargon alone is a suggestion unless it blocks those.
- The three parts (findings, design, results) must be visible at the top, outside any collapsed
  block; detail goes in a collapsed block below. This is an agreed exception to the `AGENTS.md` rule
  that agent posts are collapsed. **Fail** only if the design or results are hidden entirely inside
  a collapsed block.
