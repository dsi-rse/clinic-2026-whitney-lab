# Do the task-contract guidelines help an agent write a better contract? (#44)

**Question.** If a coding agent reads [`docs/task-contract-guidelines.md`](../../docs/task-contract-guidelines.md)
before revising a task contract, does it avoid the pitfalls we have already hit,
without adding new ones, and does the result answer as well or better?

## Design (written before the revisions and the runs)

**Three contracts.**

| Arm | What it is |
|---|---|
| `old` | `tasks/endo_myometrial_invasion.yaml` on `main` at `ad531ff`, unchanged |
| `unguided` | a fresh agent's revision of `old` |
| `guided` | a second fresh agent's revision of `old`, given the guidelines too |

The only difference between `unguided` and `guided` is the guidelines. Both
agents are the same model (Claude Opus 5.5, as a Claude Code subagent), get the
same prompt ([`inputs/revision_prompt.md`](inputs/revision_prompt.md)) apart
from one line naming the guidelines, and work in a folder holding only the old
contract, OncoTrace's `docs/task-contract.md`, and 20 example reports. The
examples are patients outside the 66 that are scored
([`inputs/example_reports.csv`](inputs/example_reports.csv), chosen with seed 44
by [`make_workspaces.py`](make_workspaces.py)). Neither agent sees this repo's
issues, experiments or annotations.

Both prompts state two facts that the guidelines also cover: the annotations use
the current value names, and report text must not be copied into a contract.
They are rules of this repo, so any agent would be told them, but it means
guidelines 6 and 14 cannot show a difference here.

**Offline checks (no model runs).**
- **Known gaps fixed.** [`inputs/known_gaps.csv`](inputs/known_gaps.csv) lists
  six gaps found in `old` by earlier work, with what counts as fixed or partly
  fixed. Each revision is scored by hand against it (fixed = 1, partly = 0.5).
- **New problems**, counted by script for all three contracts: the contract
  fails to load; a value named in a rule or in `no_quote_values` is not a
  declared value; an annotation holds a value the contract doesn't allow; a
  snake_case name in the instructions is not declared; a value with no
  definition (never named in the instructions and no comment beside it); and
  any 7-word run shared with the 66 scored reports or the 20 example reports.

**Model runs.** Each contract runs twice on the 66 annotated patients
(`experiments/endometrial_baseline_full/roster_annotated66.csv`), six runs, with
`config/endometrial_openrouter.yaml` changed only in task and roster. For
invasion and depth: correct, wrong, over-committed (a definite answer where the
annotation says not applicable or cannot be determined), abstained, and the
"always the commonest annotation" baseline. The difference between the two
`old` runs is the run-to-run variation.

**Pass bar.**
- *The guidelines help the writing* if `guided` fixes more known gaps than
  `unguided` and has no more new problems than `old`.
- *They do no harm to answers* if, for invasion and depth, `guided`'s mean
  correct count is not below `old`'s by more than the run-to-run variation (at
  least one patient), and its over-committed count is not above `old`'s by more
  than that.
- *They help answers* only if `guided`'s mean correct count beats both `old`
  and `unguided` by more than the run-to-run variation. With 66 patients this
  is unlikely, and an inconclusive result will be reported as such.

## What happened while making the revisions (added after the design above)

- Both agents ran on 2026-11-17. Their contracts and their own change notes are
  in [`contracts/`](contracts/) (`unguided.yaml`, `guided.yaml`, `*_changes.md`);
  `old.yaml` is `tasks/endo_myometrial_invasion.yaml` at `ad531ff`.
- **One difference in procedure.** A Claude Code hook stopped the guided agent
  writing into its workspace, because the workspace was outside this session's
  git worktree, so it saved its two files to the session's scratchpad and did
  not run the load check. The unguided agent wrote into its workspace from the
  shell and did run the check. Both files were copied here unchanged, and both
  load (`offline_checks.csv`).
- **Known-gap scores** are in [`inputs/gap_scores.csv`](inputs/gap_scores.csv),
  one row per contract and gap with the reason. They were scored by hand by the
  Claude Code session that wrote the guidelines and this design, reading each
  contract against the fixed/partly wording in `inputs/known_gaps.csv`. That
  session knows which revision had the guidelines, so the scores are not blind.

**Limits.** One revision per arm, so this samples one agent's behaviour each.
One annotator, not adjudicated. The two revisions may each change several
things; the question is whether the guidelines lead to a better contract, not
which edit helps. The known-gap scores are judged by hand.
