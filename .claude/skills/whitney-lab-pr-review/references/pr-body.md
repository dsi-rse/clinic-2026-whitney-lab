# How an experiment PR body must read

Applies to **experiment PRs**: self-contained work that asks a question, runs something, and reports
what happened. Annotation files, scaffolding, docs and bug fixes are exempt (item 15 is n/a).

The reader is the mentor, who isn't doing the runs and barely knows OncoTrace. They must be able to
follow the body without asking anyone. Plain words, one screen, focused.

## Required shape

**Visible at the top of the body** (outside any collapsed block). Detail goes below or in the README.

### 1. Findings (short bullets)

- One-sentence takeaway first, or 2 to 5 bullets. Each is a plain claim with its number
  ("49 of 50 patients got the same answer in all five runs").
- Say what it means for the lab, not only what was measured. Say if the result is inconclusive.

### 2. What we did (experimental design)

In plain language, in about ten lines:

- **The question**, in one sentence, and why anyone should care.
- **What was run**: on how many patients, with which tool setting, and what was compared. Name the
  one thing that differs between the groups, and what the baseline or control is.
- **What would count as an answer**: what result would mean yes, and what would mean no (written
  before the runs where possible). Define any pass bar.
- **Limits**: sample size, one annotator, anything that makes the result weak.
- **Every term defined at first use**: OncoTrace, agentic, one_shot, contract, roster, arm,
  temperature, "honest", "over-committed". If a word needs the reader to know the project, explain it
  in a clause or put a 3 to 5 line glossary right below.
- No code identifiers, flags, commit hashes or file paths in this section. Those belong in the
  detail, the README and `provenance.json`.

### 3. Results

- Before each table: one sentence saying what a row is, what a column is, and what the numbers count
  ("patients out of 50").
- Under each table: how to read it. Say which numbers to compare, what a good value looks like, and the
  **so what** in one sentence. Define every abbreviation, label and column (for example what makes an
  answer "honest").
- Include the baseline or reference row (such as always guessing "present") so the numbers can be judged.
- Every figure comes from a committed table (checklist item 12).

### Then, collapsed or linked

File table, how to run, checks, provenance, long tables, next steps. Don't repeat the README.

## Reader test (do this in Phase 1)

Read only the body, as the mentor would. Answer from the text alone:

1. What question is this asking, and why does it matter?
2. What was compared, and what single thing was changed?
3. How would the authors tell yes from no?
4. What did they find, in one sentence?
5. For each table: what is a row, what is a cell, and what should I compare?
6. What are the main limits?

Record in the notes: the **terms left undefined** (list up to 8), and each **table with no reading
guide**. If you couldn't answer 1 to 3 or 5, that is a fail even if the numbers are right.

## What good and bad look like here

- **Closest to the target:** #14. A takeaway line, a small results table with the "always present"
  baseline row, a three-patient table with a sentence explaining each row, and a clear next question.
  Its design section is still thin.
- **Good findings bullets:** #12 and #21 (the lines before the collapsed block).
- **Typical misses:** a body that is a long collapsed block with the findings above it but no design
  section; setup lines packed with identifiers (model tags, commit hashes, config names); letters or
  codes (B and C, T0 and T1) used without saying what they are; columns such as "honest" or
  "over-committed" with no definition; a table followed directly by a bullet list and no reading guide.

## Wording a fix

Say what is missing and what to add, not "make it clearer". Examples:

- "Add a short 'What we did' section: the question, the two settings compared, and what would count
  as an improvement. Define B and C where they first appear."
- "Under the results table, add one sentence on how to read it, and define 'honest' (what answer
  counts) in a footnote."
