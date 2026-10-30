# Where OncoTrace disagrees with a *definite* annotation, who is right?

**Question (issue #26):** PR #21 ran the 50 annotated patients four times. In most
disagreements the annotation itself is undetermined, and #13 / PR #22 own those.
This experiment takes the complement: the rows where the annotation gives a
definite value and the run still disagrees, so one side really is wrong.

**Why it matters:** these are the only disagreements that can move the accuracy
number in a defensible direction. If the model is wrong, the trace says which
failure mode to fix. If the annotation is wrong, the reference standard needs a
correction before any future run is scored against it.

**Scope: exactly two rows**, both the depth field `myometrial_invasion_percent`
([`inputs/rows.csv`](inputs/rows.csv)):

| Patient | Annotation | T0 / T1 r1 / r2 / r3 |
|---|---|---|
| `TCGA-A5-A0GJ` | `not_applicable` | `less_than_50` ×4 |
| `TCGA-A5-A0GR` | `less_than_50` | `less_than_50` / **`fifty_or_greater`** / `less_than_50` / `less_than_50` |

`TCGA-A5-A0GJ`'s *invasion* field also disagrees (annotation `cannot_be_determined`,
run `present` ×4), but a `cannot_be_determined` annotation belongs to #13 / PR #22,
so it is out of scope here. No third row meets "annotation is definite and the run
disagrees" — see [the results README](results/2026-10-30_002011/README.md#scope-check).

**Short answer (results: [`results/2026-10-30_002011/`](results/2026-10-30_002011/README.md)):**

| Patient | Verdict |
|---|---|
| `TCGA-A5-A0GJ` | **task contract doesn't say** — no number, no half, and not even the word "invasion" anywhere in the report; the model's half rests on unquantified-extent wording the contract has no rule for |
| `TCGA-A5-A0GR` | **model wrong** (`t1_r1` only), failure mode **fraction arithmetic wrong** — it divided a page-1 microscopic depth by a page-2 gross myometrial-thickness figure, landing on exactly 50.0% |

No report, rationale or annotation text appears in this folder. Patients are TCGA
IDs, passages are character offsets, and a 7-word leak check against the report
store runs over every file written ([`leak_check.csv`](results/2026-10-30_002011/leak_check.csv)).

## Design

- **Runs:** the four PR #21 arms, oncotrace `fc3dadc`, contract `ba27b6ce…`,
  GLM-5.3-Flash, agentic. Every commit, digest and config SHA-256 is in each
  results folder's `provenance.json`.
- **Reference:** [`annotations/endo_myometrial_invasion/`](../../annotations/endo_myometrial_invasion/),
  read through `oncotrace_bench.records`.
- **Nothing is re-run.** This is an analysis of existing runs, so it takes
  seconds on a login node and needs no GPU.

### Where the judgements live

The computed columns come from the runs. The **judged** ones — verdict, deciding
offsets, whether the earlier reading holds, failure mode, proposed annotation
label, mentor question — are hand-written in
[`inputs/verdicts.csv`](inputs/verdicts.csv), the same way PR #22 kept its
pre-registered expectations in an inputs file. The script validates them: a
verdict outside issue #26's four allowed values, or a deciding offset that
nobody actually cited, stops the run instead of being written out.

### How a passage is described without quoting it

Every deciding passage is recorded as a half-open character range into the
patient's one stitched document, the same coordinates TraceView and the
annotations use. To say *what kind* of wording sits in a range, the script
reports **wording classes** — `invasion_word`, `fraction_or_percent`,
`half_word`, `full_thickness_word`, `unquantified_extent`, `thickness_statement`
and so on. Only the class name and a count are ever written out.

The class vocabulary is the **task contract's own**
([`tasks/endo_myometrial_invasion.yaml`](../../tasks/endo_myometrial_invasion.yaml)
names "full thickness", "transmural", "invades to serosa", "superficial half",
"inner half" as the wording it has rules for), not anything read off a report.
That matters for the A0GJ verdict, which turns on wording the contract lists
*no* rule for.

**One judgment call to confirm:** `measurements.csv` and `arithmetic.csv` write
measurement **values** (`1.0 mm`, `2.0 mm`) next to their offsets. Offsets alone
cannot show that 1.0 / 2.0 is 50.0%, and issue #26 asks for every number to come
from a committed file. PR #18's `audit_14_patients.csv` already commits the same
kind of thing (`computed_percent`, "12.0/26.0 mm"), so this follows existing
practice in the repo — but it is a number from a report, and the mentor should
confirm it is acceptable.

## Layout

```text
review_disagreements.py        the one entry point: reads the runs, writes results/<timestamp>/
inputs/rows.csv                the two rows in scope, with the earlier reading and its source
inputs/verdicts.csv            the hand-written verdicts, deciding offsets and mentor questions
inputs/candidate_arithmetic.csv  the depth/thickness pairs to work out, by offset
results/<timestamp>/           one folder per analysis, with a README of the findings
```

Each results folder holds:

| File | What it holds |
|---|---|
| `verdicts.csv` | The issue #26 table: patient, field, annotation, four answers, four confidences, four `depth_basis` values, how many runs agreed, earlier reading and source, and the verdict columns joined from `inputs/verdicts.csv` |
| `run_answers.csv` | One row per patient and run: every label field, model calls, fraction of the document read, truncated replies, refusal signatures, citation counts per group |
| `evidence_spans.csv` | Every citation the four runs **and** the annotator made, as offsets, with page, measurement values and wording classes — this is the table the verdicts are read off |
| `report_vocabulary.csv` | How often each wording class occurs in the **whole** report, and where. The zero rows carry the argument: a report that never states a half cannot support a definite half |
| `measurements.csv` | Every mm/cm measurement in the two reports, by offset and page, with what the preceding 40 characters are about |
| `arithmetic.csv` | Each candidate depth-over-thickness pair worked out, and the label it gives |
| `scope_check.csv` | Every disagreement in all 200 patient-runs, grouped by annotation value and labelled with which issue owns it, so the choice of two rows can be checked |
| `leak_check.csv` | For each file written, how many 7-word runs it shares with either report (0 = clean) |
| `summary.txt`, `provenance.json` | The printed numbers, and what the folder was made from |

The analysis reuses `src/oncotrace_bench/records.py` (runs, annotations, reports,
read windows, coverage) and `provenance.py`.

### What is not in Git, and where it is

| What | Where |
|---|---|
| The four runs | `/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/2026-10-23_temperature_{t0,t1_r1,t1_r2,t1_r3}/` |
| The report store | `/net/spaces/annawoodard/oncotrace/data/endometrial/documents/ucec_pathology_report.jsonl` |

Both are readable by the `__oncotrace` group.

## Reproduce it

You need to be in the `__oncotrace` group (`id -nG` lists it) and have the
clinic environment from [`docs/student-setup.md`](../../docs/student-setup.md).
Run from the repo root; it takes seconds and uses no GPU.

```bash
make definite-disagreements
```

or directly:

```bash
PYTHONPATH=src python experiments/definite_disagreements/review_disagreements.py
```

The CSVs in your new `results/<timestamp>/` should be byte-identical to the
committed ones. To read other runs, pass them explicitly:

```bash
make definite-disagreements ARGS="--run t0=<run> --run t1_r1=<run> --run t1_r2=<run> --run t1_r3=<run>"
```

### Looking at the same spans in TraceView

The offsets in `evidence_spans.csv` are document offsets, so they can be opened
next to the report in TraceView from an OncoTrace clone:

```bash
PYTHONPATH=~/oncotrace:~/oncotrace/viewer python -m viewer --run /net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/2026-10-23_temperature_t1_r1 --task tasks/endo_myometrial_invasion.yaml
```

`src/oncotrace_bench/traceview_summary.py` wraps the same loader for scripts
(`add_traceview_to_path`, `load_views`, `trajectory_facts`) if you want the
text-free trajectory summary instead of the viewer.

## Caveats

- **Two rows.** Nothing here is a rate. These are two hand-read cases.
- **One annotator, not adjudicated,** and 45 of the 50 patients come from one
  tissue source site. A disagreement is not evidence that the annotation is the
  truth; that is the whole reason this issue exists.
- **A0GR's verdict rests on a judgment about a measurement, not on arithmetic.**
  The arithmetic is checkable; whether a gross thickness figure from another
  page is the right denominator is a clinical question, written out for the
  mentor in the results README.
- **A0GJ is deliberately left un-blamed.** Whether unquantified-extent wording
  means `less_than_50` is the open #15 question. Until the mentor answers it,
  calling the model wrong here would be assuming the answer.
- The reports are OCR'd scans from roughly 2000–2013. Wording classes are regex
  matches over that OCR, so a garbled word can be missed.
