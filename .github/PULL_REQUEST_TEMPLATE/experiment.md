<!--
Use this template for experiment PRs only.
An experiment PR asks a question, runs something, and reports what happened.
Other PR types (annotations, scaffolding, docs, bug fixes) do not use it.

To use it, add ?template=experiment.md to the compare URL, or run:
gh pr create --template .github/PULL_REQUEST_TEMPLATE/experiment.md

Keep the three parts below outside any collapsed block.
The full rules are in AGENTS.md, section "Experiment PR descriptions".
-->

## Findings
<!-- Write one sentence, or 2 to 5 short bullets.
Each bullet is a plain claim with its number.
Example: "49 of 50 patients got the same answer in all five runs."
Say what the result means for the lab.
If the result is inconclusive, say so. -->

## What we did
<!-- Write about ten lines in plain language.
Do not use code identifiers, flags, hashes or file paths here.
- Say the question in one sentence. Say why it matters.
- Say what was run: how many patients, and what was compared.
- Name the one thing that differs between the groups. Name the baseline or control.
- Say what result counts as yes and what counts as no. Write this before the runs where possible. Give the pass bar, if there is one.
- Say the main limits. Examples: small sample, one annotator.
- Define every term the first time you use it.
Findings and this section should fit on about one screen. -->

## Results
<!-- For each table:
- Before it, write one sentence: what is a row, what is a column, what do the numbers count?
- Under it, say how to read it: which numbers to compare, what a good value looks like, and the so-what in one sentence.
- Define every abbreviation and label.
- Include a baseline or reference row, so the reader can judge the numbers.
- Every figure must come from a committed table. -->

<details>
<summary>Details: files, how to run, checks, provenance, long tables</summary>

### Files and how to run
<!-- Add the file table, the exact commands from a fresh clone, and the run time. Do not repeat the README. -->

### Reproducibility checklist (AGENTS.md, section "Reproducibility")
- [ ] 1. Runs, edited inputs and intermediate files are in a shared, group-readable path. Every script and config behind a table is committed. For protected files, the README says where they are, who can read them, and their SHA-256, and a committed spec regenerates them. I checked access as another person.
- [ ] 2. Every number cites a results table made by committed code. Hand checks say how they were done and list the patient IDs. Tables were regenerated after every change.
- [ ] 3. The analysis reruns from a fresh clone. The README has the exact commands. Dependencies and environment variables are declared. Scripts take paths as arguments (no `/home/<user>` defaults). The README says what reproduces exactly and how long the rerun takes.
- [ ] 4. The PR says what cannot be rerun, which runs were resumed or split, and which unmerged PRs it depends on.

### Provenance
<!-- Link to provenance.json or the results folder (issue #31). -->

</details>
