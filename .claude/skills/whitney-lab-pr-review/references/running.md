# Running the PR

The lab's reproducibility test is literal: a teammate clones the repo, follows the README, and gets
the committed numbers. This file is how you play that person.

## 1. Fresh clone

Work in the scratchpad, never in the TA's checkout.

```bash
git -c credential.helper= -c credential.helper='!gh auth git-credential' clone -q \
  https://github.com/<owner>/<repo> <scratch>/pr-<n>        # `gh repo clone` uses SSH and may fail
cd <scratch>/pr-<n> && git fetch -q origin pull/<n>/head:pr<n> && git checkout -q pr<n>
git log --oneline -5 && git rev-list --left-right --count origin/main...HEAD
```

A branch behind `main` is a suggestion. A merge conflict is a requested change.

## 2. Follow the README

Do the steps in order and nothing else. Every guess or fix is a finding. Run README commands exactly
as written (no `python -I`: it breaks imports from the script's directory).

- Use a venv in the scratchpad with the repo's pins (`pip install -e .`, `ruff` at the pinned
  version). Add packages only when the README omits them, and report each (e.g. `httpx`, `pyyaml`).
- Check whether the runs, inputs and edited files the README names are **readable by you**. List
  each unreadable path; it is a finding (item 12), and anything depending on it is **could not
  verify**.
- Never commit or paste secrets. A committed key is the top finding.

## 3. Lint and shortcuts

```bash
ruff check . ; ruff format --check .      # pre-commit may not be installed; say so
git diff origin/main...HEAD --name-status | grep -v '^A'                  # deleted or modified files
git diff origin/main...HEAD | grep -nE '^\+.*(noqa|type: ignore|skip|xfail)'
git diff origin/main...HEAD --stat -- AGENTS.md CLAUDE.md pyproject.toml .pre-commit-config.yaml Makefile src
```

A failure that already exists on `main` isn't this PR's fault.

## 4. Rerun the analysis

Run the PR's analysis or comparison script on the real run folders, writing to a scratch output
folder, then diff against the committed results:

```bash
cmp <scratch-out>/<table>.csv <committed>/<table>.csv        # or: diff <(tr -d '\r' < a) <(tr -d '\r' < b)
```

- Byte-identical is the target. Report any difference and the rows involved.
- If the runs are unreadable, rerun on any accessible run as a **smoke test** (does the script
  work?), and say it proves nothing about the PR's numbers.
- GPU/Slurm reruns are **could not verify**.
- Notebooks (rare): run in README order into a separate folder. Don't overwrite the author's.
- Docker: only if a Dockerfile exists.

## 5. Number audit

1. Copy every figure from the PR body, the README and any new `*.md` in the diff.
2. Map each to a committed table or script output. Recompute cheap ones from the committed CSVs.
3. Mark each **matches**, **differs** (give both values), or **no source**.
4. Qualitative claims ("the same patients in all runs") count too. Check them or mark them unchecked.

Report only the **differs** and **no source** rows.

## 6. Provenance check

Read `provenance.json`. For each commit it records, run `gh api repos/<owner>/<repo>/commits/<sha>`.
Check `uncommitted_files`, `oncotrace_modified`, and what the record leaves out (job IDs, config
hash, model, seed).

## 7. Record everything

Keep each command and its one-line outcome for the notes. Remove the scratch clone and any scratch
outputs when done.
