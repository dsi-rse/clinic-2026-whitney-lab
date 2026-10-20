# Does OncoTrace follow the evidence? (issue #8)

**Question:** when OncoTrace answers the myometrial-invasion task, does the answer come from the report text, or from a prior that it then justifies with citations?

**Why it matters:** if the answer comes from a prior, a correct-looking citation tells us nothing, and fixing OncoTrace's harness would not make the answers more trustworthy. This experiment measures that, and can be re-run after an OncoTrace fix or with more annotations to see whether things improved.

**Short answer (latest results: [`results/2026-10-20_165341/`](results/2026-10-20_165341/README.md)):**
- **When a report states depth clearly, the answer follows the text.** Flipping every depth statement to the other half flipped the answer in 9 of 9 patients. Rewording the same statements changed nothing in 9 of 9. Unedited reruns changed 1 answer in 67.
- **The open weakness is ambiguous or missing evidence.** The model almost never answers `cannot_be_determined`, and its stated confidence doesn't reflect when it's unsure.

No report, rationale, or annotation text appears in this folder. Patients are TCGA IDs, and passages are half-open character offsets `[start, end)` into the patient's single report document.

## Design

The experiment has two parts.

**Part 1** reads the original OncoTrace run (GLM-5.3-Flash, agentic, oncotrace `e901b3f`, [`config/endometrial.yaml`](../../config/endometrial.yaml), temperature 0) and compares it with the 50 annotated patients in [`annotations/`](../../annotations/endo_myometrial_invasion/): field agreement, cited vs annotated passages, how much was read before answering, why patients ended with no answer, and whether refusals changed answers.

**Part 2** edits the reports and reruns OncoTrace on them.
- 9 annotated patients where the original run matched the annotation on both label and half: 6 `<50`, 3 `≥50`.
- Each arm reads its own edited copy of the reports; the originals are untouched. Unit and document IDs are unchanged, so runs pair by patient.

| Arm | Edit | Expected if the model follows the evidence |
|---|---|---|
| Flip | Rewrite every definitive depth passage to the other half, consistently (17 passages, including mm figures and one stage, pT1b → pT1a) | Percent moves to the other half |
| Reword | Same passages, same meaning and half, different wording | Unchanged |
| Unedited ×3 | None; 24 patients, 3 new server starts | Unchanged (measures run-to-run noise) |

## Layout

```text
run_experiment.py             the one entry point: analyzes the runs, writes results/<timestamp>/
evidence_alignment.py         Part 1: field agreement, cited vs annotated passages, reading coverage
triage_no_answers.py          Part 1: why each no_answer happened, and whether refusals changed answers
evidence_inventory.py         Part 1: depth passages per report, and which patients can be edited
compare_arms.py               Part 2: each patient's answer across the original run, reruns and edit arms
report_edits.py               Part 2 setup: builds an arm's edited reports from a hand-written spec
check_traceview_citations.py  separate check that citations highlight the right words in TraceView
configs/<arm>.yaml            OncoTrace run configs for the control, flip and reword arms
inputs/                       text-free inputs: curated passages, rosters, edit manifests, checksums
results/<timestamp>/          one folder per run of the experiment, with a README of its findings
```

Code other analyses can reuse lives in `src/oncotrace_bench/`: `records.py` (load runs, annotations and reports; span overlap) and `provenance.py` (what a result folder was made from).

### What is not in Git, and where it is

Some inputs hold report text, so they stay on the cluster. Everything below is readable by the `__oncotrace` group.

| What | Where |
|---|---|
| Original reports | `/net/spaces/annawoodard/oncotrace/data/endometrial/documents/ucec_pathology_report.jsonl` |
| Edit specs (`edit_spec_flip.json`, `edit_spec_reword.json`) and edited reports (`<arm>/ucec_pathology_report.jsonl`) | `/net/spaces/annawoodard/oncotrace/workspaces/khyatt/analysis/issue8/inputs/` |
| The six runs read by `run_experiment.py` | `/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/` (`2026-10-09_endometrial_glm53`, `2026-10-13_issue8_{s1,s2,s3}_control`, `2026-10-13_issue8_{flip,reword}`) |

`inputs/shared_inputs.sha256` holds the checksums of the shared files, so you can check you have the same ones.

## Reproduce it

You need to be in the `__oncotrace` group (`id -nG` lists it) and have the clinic environment from [`docs/student-setup.md`](../../docs/student-setup.md). Run every command from the repo root.

### 1. Re-run the analysis on the existing runs (minutes, CPU)

```bash
make evidence-following
# or directly:
PYTHONPATH=src python experiments/evidence_following/run_experiment.py
```

This writes `results/<timestamp>/`. Its CSV and JSON tables should be byte-identical to the ones in `results/2026-10-20_165341/`:

```bash
cd experiments/evidence_following/results
for f in 2026-10-20_165341/*.csv 2026-10-20_165341/*.json; do
  cmp -s "$f" "<your folder>/$(basename "$f")" && echo "same $f" || echo "DIFF $f"
done
```

(`provenance.json` and `summary.txt` will differ: they record when, where and from which commit the folder was made.)

If a run file will not open (`Permission denied`), ask Kaden to run `chmod -R g+rX` on that run folder.

### 2. Rebuild the edited reports (seconds, CPU)

The edited reports are made from the edit specs, so you can check them without trusting the shared copies:

```bash
CLINIC=$PWD
mkdir -m 700 /tmp/$USER-edits
cp /net/spaces/annawoodard/oncotrace/workspaces/khyatt/analysis/issue8/inputs/edit_spec_*.json /tmp/$USER-edits/
for arm in flip reword; do
  PYTHONPATH=src python experiments/evidence_following/report_edits.py apply --arm $arm --inputs /tmp/$USER-edits
done
cd /tmp/$USER-edits && grep -v ' control/' $CLINIC/experiments/evidence_following/inputs/shared_inputs.sha256 | sha256sum -c
```

Every line should say `OK`, and `report_edits.py` should say the roster and manifest match the committed copies. Delete `/tmp/$USER-edits` afterwards: it holds report text.

### 3. Re-run OncoTrace on the arms (hours, 4 GPUs)

This repeats Part 2 from scratch. For an exact repeat, use an OncoTrace checkout at `e901b3f`.

1. Start a GLM-5.3-Flash server as in OncoTrace's running guide, or copy the `serving:` block from your own `config/endometrial_local.yaml` into a local copy of each arm config. The configs in `configs/` attach to a server with `--base-url`. They match the configs used for the original arm runs except for the personal serving block and the paths to the rosters.
2. Check each config resolves. It should print `unit_count` 24 (control) or 9 (flip, reword) and contract `940b2a7b...`:

   ```bash
   CONFIGS=$PWD/experiments/evidence_following/configs
   cd ~/oncotrace
   PYTHONPATH=$PWD PYTHONNOUSERSITE=1 python -m oncotrace.runner check --config $CONFIGS/control.yaml --output /tmp/$USER-none
   ```
3. Give every arm a fresh, empty run folder in your own workspace, e.g. `$WS/runs/$(date +%F)_issue8_flip`. OncoTrace skips any patient that already has a record, even when the report was edited.
4. Run each arm against the server (one server start per control repeat; three repeats measure noise):

   ```bash
   PYTHONPATH=$PWD PYTHONNOUSERSITE=1 python -m oncotrace.runner extract --config $CONFIGS/<arm>.yaml --output <run folder> --base-url <server URL>
   ```
5. Make the records readable by the group: `chmod -R g+rX <run folder>`. The configs set `artifacts: group_readable: true`, but OncoTrace's Slurm scripts set `umask 077`, which still leaves the record files owner-only.
6. Analyze your runs:

   ```bash
   make evidence-following LABEL=rerun ARGS="--controls <run> <run> <run> --arm flip=<run> --arm reword=<run>"
   ```

Answers can differ a little from run to run (1 in 67 in our reruns), so compare the counts in the results README, not the CSVs byte for byte.

## Re-run it later

**After an OncoTrace fix** (for example dsi-rse/oncotrace#6): make new runs with the fixed OncoTrace (step 3), then run the analysis on them with a label, e.g. `LABEL=after-fix6`. Compare with the previous results folder: whether the no-answer count in `no_answer_triage.csv` falls, and whether the flip and reword arms still behave as expected. Decide with your mentor what counts as an improvement before the new run.

**With more annotations:** add annotation files under `annotations/` and run the analysis again. Part 1 covers more patients. Part 2 does not change unless you add patients to the arms, which needs new edit specs (`report_edits.py template`, then fill in each replacement by hand) and new runs.

**Every new results folder** gets a `README.md` with what it was made from. Write its key findings in your own words before committing it.

## Next

1. **Removal experiment:** delete all depth evidence versus delete unrelated text of the same length. The contract's expected answer is `cannot_be_determined`, which directly tests the over-commitment above. Candidates and controls are already chosen (`evidence_inventory.json`).
2. **Rerun with the #6 fix:** rerun the patients affected by #5 with the fix, and raise `max_completion_tokens` to 16384.
3. **Open questions for the mentor:**
   - Should a stage that names no edition read pT1b as AJCC 6th (`<50`) or 7th (`≥50`)?
   - Is a stage-only report `cannot_be_determined`, including when only pT2 remains?
   - How should boundary wording (about one-half, 50%) be resolved?
   - Should the experiments keep temperature 0 or move to the model's 1.0 / 0.95?
