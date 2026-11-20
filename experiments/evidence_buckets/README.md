# Can each answer say how well the report supports it?

**Question:** can OncoTrace label every invasion and depth answer with how the report supports it, so that only the shaky answers go to a person? The four categories are:

- **Confident:** the report states it;
- **Implied:** it follows from the report, at a stated confidence;
- **Uncertain:** the report touches the question but does not settle it;
- **Not present:** the report does not address it.

This is issue #55.

**Why it matters:** today a reviewer cannot tell an answer the report states from one the model reasoned its way to. They also cannot tell "not mentioned" from "mentioned but unclear". #42's A0GJ is the example: a definite depth answer from wording that gives no depth.

**Short answer:** see [`results/2026-11-17_213905/`](results/2026-11-17_213905/README.md).
- The flags on depth point at the right answers. They hold 38–43% of depth disagreements against 15–20% of depth answers.
- The model calls nearly everything Confident.
- It never uses Not present.
- It does not flag the cases the annotator left undetermined.

No report, rationale or annotation text appears in this folder. Patients are TCGA IDs.

## Design

- **Patients:** the 66 annotated patients ([`../endometrial_baseline_full/roster_annotated66.csv`](../endometrial_baseline_full/roster_annotated66.csv)), scored against [`annotations/`](../../annotations/endo_myometrial_invasion/).
- **Model:** GLM-5.3-Flash through OpenRouter, provider `wafer/us`, temperature 0. The settings are those of [`config/endometrial_openrouter.yaml`](../../config/endometrial_openrouter.yaml). OncoTrace `d4b7fd3`, agentic.
- **Two arms, run side by side:** the arms ran at the same time, so a change at the provider affects both alike. Each arm ran its two repeats one after the other.

| Arm | Config | Task contract | Runs |
|---|---|---|---|
| baseline | [`configs/baseline.yaml`](configs/baseline.yaml) | [`tasks/endo_myometrial_invasion.yaml`](../../tasks/endo_myometrial_invasion.yaml), unchanged | 2 |
| evidence | [`configs/evidence.yaml`](configs/evidence.yaml) | [`endo_myometrial_invasion_evidence.yaml`](endo_myometrial_invasion_evidence.yaml) | 2 |

The two configs differ only in their `task:` line.

**The evidence contract** is a copy of the main one. Every change in it is marked `EVIDENCE BUCKETS`:

- **Category fields:** two new answers, `myometrial_invasion_evidence` and `myometrial_invasion_percent_evidence`. Each holds `explicit`, `implied_high`, `implied_medium`, `implied_low`, `uncertain` or `not_present`; the depth field also allows `not_applicable`. OncoTrace reads an answer as only a value and its quotes, so the category must be a separate field beside it.
- **`uncertain`:** a new value for invasion and depth. It needs quotes.
- **`cannot_be_determined` needs no quote:** it is added to `no_quote_values`, because it means Not present.
- **Rules:** they tie each category to its values in both directions. For example, `present` must be `explicit` or `implied_*`, and `uncertain` must be `uncertain`.
- **Instructions:** they say when each category applies.

[`check_contract_rules.py`](check_contract_rules.py) runs 13 made-up submissions through OncoTrace's own answer check. It needs no model and no reports.

**Pass bar (set in #55 before the runs):**
- **Useful:**
  - flagged answers (`implied_*` or `uncertain`) hold a larger share of the disagreements than of all answers;
  - `explicit` answers agree at least as often as the baseline answers.
- **Safe:** the main answers change between arms on no more patients than between the two baseline runs.

`pass_bar.csv` computes both.

## Layout

```text
endo_myometrial_invasion_evidence.yaml   the evidence contract (copy of tasks/endo_myometrial_invasion.yaml)
configs/<arm>.yaml                       OncoTrace run configs, baseline and evidence
check_contract_rules.py                  offline check that the contract accepts and refuses what it should
run_arms.sh                              runs both arms on OpenRouter, REPEATS times each
compare_arms.py                          reads the runs, writes results/<timestamp>/
results/<timestamp>/                     one folder per analysis, with a README of its findings
```

Each results folder holds:

| File | What it holds |
|---|---|
| `patients.csv` | One row per run and patient: status, answers, categories, annotations, agreement state, quote counts, confidence, calls |
| `per_run.csv` | Per run: answered, refusals (submissions OncoTrace refused before accepting one), mean calls, and how many answers were `cannot_be_determined` (and of those, how many carry quotes) or `uncertain` |
| `four_way.csv` | Per run and answer: correct, wrong, over_committed (definite answer where the annotation is undetermined or not applicable), abstained (`uncertain` or no answer). A `cannot_be_determined` answer against a definite annotation counts as wrong. The "always …" row gives the commonest annotation to every patient |
| `categories.csv` | Evidence runs: per answer and category, the number of answers and their four-way split |
| `flagged_share.csv` | Evidence runs: flagged answers and flagged disagreements, out of all of each |
| `pass_bar.csv` | The pass bar, test by test, with `passes` and the patients behind each answer change |
| `answer_changes.csv` | Every pair of runs: patients whose invasion or depth answer differs. `changed_beyond_cbd` counts `uncertain` and `cannot_be_determined` as one answer |
| `annotated_cbd_split.csv` | Where the annotation is `cannot_be_determined`: what the model answered |
| `definite_annotation_model_cbd.csv` | Patients with a definite annotation who got `cannot_be_determined` |
| `depth_basis_vs_category.csv` | Evidence runs: the annotations' `depth_basis` against the model's depth category |
| `review_queue.csv` | Evidence runs: patients with at least one flagged answer, and how many of them, and of the rest, disagree with the annotations |
| `watched_patients.csv` | #42's A0GJ and A0GR in every run |
| `summary.txt`, `provenance.json` | The printed tables, and what the folder was made from |

The analysis reuses `src/oncotrace_bench/records.py` and `provenance.py`, and scores answers as TraceView's `scoring.agreement_state` does.

### Results folders

| Folder | Status |
|---|---|
| `results/2026-11-17_213637/` | First analysis. It has no `pass_bar.csv`; its other CSVs are identical to the next folder's. Superseded |
| `results/2026-11-17_213905/` | Current. Adds `pass_bar.csv` |

### What is not in Git, and where it is

| What | Where |
|---|---|
| The four runs read by `compare_arms.py` | `/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/2026-11-18_evidence_buckets_{baseline,evidence}/rep{1,2}/`, readable by the `__oncotrace` group. They were made on kh's laptop through OpenRouter and copied there with rsync on 2026-11-20, so `provenance.json` records the laptop paths and acknowledges that they were not yet shared |
| A stalled first attempt | `runs/2026-11-17_evidence_buckets_{baseline,evidence}/rep1/` in the same folder. The laptop went to sleep and the runs stopped after 5 (baseline) and 6 (evidence) patients. They are not used in any table and are kept as a record |

## Reproduce it

You need the clinic environment from [`docs/student-setup.md`](../../docs/student-setup.md), and membership of the `__oncotrace` group (`id -nG` lists it) to read the run folders above. Run every command from the repo root.

### 1. Re-run the analysis on the existing runs (seconds)

```bash
PYTHONPATH=src python experiments/evidence_buckets/compare_arms.py \
  --run baseline_rep1=<runs>/2026-11-18_evidence_buckets_baseline/rep1 \
  --run baseline_rep2=<runs>/2026-11-18_evidence_buckets_baseline/rep2 \
  --run evidence_rep1=<runs>/2026-11-18_evidence_buckets_evidence/rep1 \
  --run evidence_rep2=<runs>/2026-11-18_evidence_buckets_evidence/rep2
```

or `make evidence-buckets ARGS="--run baseline_rep1=<run> ..."`. The CSV files and `summary.txt` in your new `results/<timestamp>/` should be byte-identical to the committed ones.

### 2. Check the contract offline (seconds, no model)

```bash
PYTHONPATH=src:<oncotrace clone> python experiments/evidence_buckets/check_contract_rules.py
```

It should print `13 of 13 cases behave as expected`. To check that each config resolves, run `python -m oncotrace.runner check --config experiments/evidence_buckets/configs/evidence.yaml --output /tmp/none`. It should report 66 units.

### 3. Re-run OncoTrace on both arms (about 3 h on a laptop, OpenRouter)

Use an OncoTrace checkout at `d4b7fd3` and the data from `scripts/endometrial_data/download.sh`. The key must be in `.env`.

```bash
set -a; source .env; set +a
RUNS=runs ONCOTRACE_REPO=<oncotrace clone> PYTHON=python DATE=<new date> \
  bash experiments/evidence_buckets/run_arms.sh
```

It uses 2 workers per arm and refuses to reuse a run folder. The original runs took from 00:43 to 03:36 UTC on 2026-11-18. The cost was estimated at about $1 in total before the runs and was not measured.

OpenRouter runs cannot be repeated bit for bit, even at temperature 0: the two baseline runs already differ on one patient. Compare the counts, not the CSVs.

## Caveats

- 66 patients, mostly from one tissue source site, and one annotator who did not mark answers as explicit or implied. Only `depth_basis` serves as a partial answer key (`depth_basis_vs_category.csv`).
- Two runs per arm. The "safe" test compares against a single pair of baseline runs.
- Too few invasion answers were flagged (0 and 1) to judge the invasion flag.
- The model used only `implied_high`, so the confidence levels inside Implied are untested.
- OncoTrace cannot forbid a quote on a Not present answer or check that a quote states the value. That did not matter here, because no answer was `cannot_be_determined`.
