# Whitney lab PR review: #<n> <PR title>

**Repo:** <url> · **Author:** @<login> · **Task:** #<issue> · **Reviewed:** <date> at `<head sha>` · **Draft:** <yes/no> · **Closes:** <#n or none>

## Verdict: <Ready to merge | Changes requested | Needs mentor decision | Could not verify>

<One or two sentences: what the PR does and the main reason for the verdict. You make the final call.>

<Follow-up only: "**From the last review:** 1 done · 2 not addressed · 3 replied (reason holds) — <what's left>".>

## Key findings

At most five, most important first. Each is evidence for the TA, not text for the author.

1. **<Title>** (blocking): <what is wrong and why it matters>. <What fixing it looks like.> Evidence: `<file:line>`; <what you ran or read>.
2. ...

**For the mentor to decide:** <pass bars, clinical conventions, closing the issue, budget. One line each, or "none".>

**Optional suggestions** (at most three, only if worth the author's time; otherwise write "none"): <...>

**What's working:** <one or two specific things>

## Number audit

Only rows that differ or have no source.

| Claim (where) | Value in text | Source / recomputed | Status |
|---|---|---|---|
| <e.g. "B 7/11", PR body> | 7 | `contract_summary.csv`: 1 | differs |

**Rerun:** <script> on <runs> → <byte-identical | N differences | could not run: why>.

## Body readability (experiment PRs; skip otherwise)

Read as the mentor would, before the README.

- **Findings:** <present and plain | missing | buried>
- **Design:** <question, what was compared, what counts as an answer, limits: which are missing>
- **Terms left undefined:** <up to 8>
- **Tables with no reading guide:** <which>
- **Fix to ask for:** <what to add, one or two lines>

## Acceptance criteria (issue #<n>)

| Criterion | Status | Evidence |
|---|---|---|
| <...> | met / partly / not met | <file> |

## Checklist

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 1 | Runs from a fresh clone | | |
| 2 | Notebooks (if any) | n/a | |
| 3 | Documented, clear purpose | | |
| 4 | No dead code | | |
| 5 | Decision and scoring rules correct | | |
| 6 | Ruff and shortcuts | | |
| 7 | AGENTS.md followed | | |
| 8 | Issue link and PR status | | |
| 9 | Solves the task | | see acceptance criteria |
| 10 | Coherent with the repo | | |
| 11 | Experiment design | | |
| 12 | Numbers sourced and rerunnable | | see number audit |
| 13 | No leakage | n/a | |
| 14 | Provenance recorded and checkable | | |
| 15 | Body readable by an outsider (experiment PRs) | | see body readability |

Collapse consecutive n/a rows into one line if there are several.

## Flags

<Only if any: new `noqa`, lint or AGENTS.md edits, deleted tests, unrelated changes, dependence on another PR. One line each, with the file.>

## What I ran

- `<command>` → <outcome>

## Could not verify

- <what, why, and what the TA would need to do>
