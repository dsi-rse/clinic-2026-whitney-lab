# TraceView filters and summaries: what exists and what we added

Checked 2026-10-15 against the OncoTrace clone's TraceView (`viewer/`), read-only.

## Already there (in the clone's working tree, uncommitted)

- **No answer, by reason**: a table on the run overview with patient counts per
  recorded reason, how many were refused repeatedly, how many had a cut-off
  reply, and links to the first patients.
- **Units tab filters**: "why no answer" and "refused" (at least once, or the
  same refusal repeated), combinable with model status and confidence.
- **Agreement by confidence** on the score page.

These edits are not on `origin/main` of OncoTrace; we did not change them.
`confidence_table.py` depends on the last one.

## Gaps found

1. The overview text says the Units tab filters on "cut off", but no cut-off
   filter exists. 106 patients were cut off at least once and still answered,
   so "why no answer" cannot find them.
2. Nothing groups refusals by signature across the run, which is how the
   1-character-quote problem was found.

## What we added (clinic repo only)

`scripts/find_patients.py`, built on `oncotrace_bench.traceview_summary`
(`find_units`, `refusal_summary`), reading records through TraceView's loader.
Usage is in `scripts/README.md`. Results on run `endometrial_glm53_20261012`:

- `--answered --cut-off`: 106 patients; `--no-answer --reason truncated_without_tool_call`: 12.
- `--refused-with citation_quote_not_found`: 84 patients, 26 of them unanswered.
- `--summary`: `quantified_depth_not_classified` affected the most patients (260,
  252 of which still answered); `citation_quote_not_found` caused the most
  refusals (635) and the most unanswered patients (26).

## For the mentor

These two gaps are general (not specific to this study). If useful they could
be added to TraceView upstream; that is a change to OncoTrace, which we did not
make.
