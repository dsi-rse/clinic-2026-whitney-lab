### Scripts directory

This directory contains runnable Python scripts. Each script should use `argparse`, import its core functionality from `oncotrace_bench`, and be documented here and in the root README.md.

#### `evidence_alignment.py` (issue 8)

Compares an OncoTrace run with the human annotations: field agreement, whether
the run cites the annotated decisive passages (or other passages), and how much
of the report the model had read before it answered. Logic lives in
`oncotrace_bench/alignment.py`.

```bash
python scripts/evidence_alignment.py            # default run, annotations, reports
python scripts/evidence_alignment.py --help     # to point at another run or output folder
```

Writes `alignment_annotated.csv` (one row per annotated patient),
`alignment_spans.csv` (one row per annotated span and run citation, offsets
only) and `reading_coverage_run.csv` (one row per run record) to the issue 8
analysis folder, then prints a summary. Outputs hold IDs, offsets, labels, and
numbers only, never report text.

#### `evidence_inventory.py` (issue 8)

Design aid for counterfactual report edits. Reads a hand-curated list of every
passage in each candidate report that bears on myometrial invasion
(`curated_passages.jsonl` in the issue 8 analysis folder: offsets, category,
tag, no text) and adds which passages the annotation and the run cited, how
many passages a percent flip or a remove-all edit would have to change, and
length-matched unrelated control passages. Candidates are annotated patients
with `present` and a definite half that the run answered correctly. Logic
lives in `oncotrace_bench/evidence_inventory.py`.

```bash
python scripts/evidence_inventory.py            # default curated file, run, annotations
python scripts/evidence_inventory.py --help     # to point elsewhere
```

Writes `evidence_inventory.json` and `edit_candidates.csv` to the issue 8
analysis folder and prints counts per classification and ranked shortlists.

#### `triage_no_answers.py` (issue 8)

Explains why patients end with `no_answer` and whether harness refusals
change the model's answer. Each no_answer patient gets a class: (a) evidence
not found, (b) refused-submission loop, (c) other budget exhaustion, (d)
truncation at `max_completion_tokens`, (e) server error. Refused submits are
not logged with their arguments, so the values the model tried to submit are
read from its reasoning ("field: value"), an estimate. Logic lives in
`oncotrace_bench/triage.py`.

```bash
python scripts/triage_no_answers.py            # default run and annotations
python scripts/triage_no_answers.py --help     # to point at another run or output folder
```

Writes `no_answer_triage.csv` (one row per no_answer patient) and
`refusals_run.csv` (one row per patient: refusal counts per signature, first
attempted vs accepted label/percent/depth basis) to the issue 8 analysis
folder, then prints a summary. Outputs hold IDs, counts, labels, and numbers
only, never report or reasoning text.

#### `check_traceview_citations.py` (issue 8)

Checks that every citation in a run opens at the right words in TraceView.
Start TraceView on the run first (see `docs/student-setup.md`), then pass the
patients to check. For each one, the script fetches the patient's page from
the running viewer and confirms that each cited passage, sliced from the
report by its offsets, is highlighted under its citation group.

```bash
python scripts/check_traceview_citations.py --port 8742 --units TCGA-A5-A2K2 TCGA-A5-A0GQ
```

Prints one line per patient (`OK` or `MISSING`, with found/total per group).
Nothing is written to disk, and no report text is printed.

#### `report_edits.py` (issue 8)

Makes edited copies of reports for one experiment arm (`flip`, `reword`,
`remove`, `remove_control`) without touching the original store. Step 1 writes
a spec listing each passage to edit (from `evidence_inventory.json`) with an
empty `replacement`; a person fills those in by hand; step 2 checks the spec
(original text unchanged, no overlaps, no blank flip/reword replacements) and
writes `inputs/<arm>/` with the edited store, its roster, and a text-free
`edits.json` of old and new offsets. Logic lives in
`oncotrace_bench/report_edits.py`.

```bash
python scripts/report_edits.py template --arm flip --units TCGA-A5-A0GI TCGA-A5-A0GM
python scripts/report_edits.py apply --arm flip
```

Specs and outputs hold report text, so they stay in the private analysis
folder. The script prints only counts and problems.

#### `compare_arms.py` (issue 8)

Lines up each patient's answer (status/label/percent) across the original run,
the unedited control repeats, and the edit arms. For edit arms it also says
whether the answer moved as expected (flip: to the other half; reword:
unchanged) and how many depth citations land on the edited passages. Logic
lives in `oncotrace_bench/arm_comparison.py`.

```bash
python scripts/compare_arms.py \
    --controls runs/2026-10-13_issue8_s1_control runs/2026-10-13_issue8_s2_control runs/2026-10-13_issue8_s3_control \
    --arm flip=runs/2026-10-13_issue8_flip --arm reword=runs/2026-10-13_issue8_reword
```

Writes `control_noise.csv` and `arm_comparison.csv` (IDs, labels, counts only).
