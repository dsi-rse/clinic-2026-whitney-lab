# How the span and confidence metrics are implemented

This page explains how [src/oncotrace_bench/metrics.py](../src/oncotrace_bench/metrics.py)
works, so you can read it, use it on a run, and change it. The short version, with
a table of every metric, is in the "Scoring spans and confidence" section of the
[README](../README.md). The metric set was proposed for issue #52.

## What it does, in one picture

```
 a run's answer for one patient          a person's annotation for the same patient
 ┌───────────────────────────────┐       ┌────────────────────────────────────┐
 │ label        "one_tumor"      │       │ value   "one_tumor"                │
 │ confidence   "high"           │       │ spans   [ place 1, place 2 ... ]   │
 │ quotes       [ place A, ... ] │       │         (where the evidence is)    │
 └───────────────┬───────────────┘       └─────────────────┬──────────────────┘
                 │                                         │
                 └──────────── compare ────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
   label right or wrong?    did the quotes land      how sure was the model,
   (already in OncoTrace)   on the marked places?    and was it right?
                            (span scores)            (confidence score)
```

Only positions, labels and confidence levels are used. No report text is read.

## The logic, step by step

| Step | What happens | Takes in | Done by | Gives out |
|---|---|---|---|---|
| 1. Load the run | Read every patient's answer from a run folder | `runs/<run>/` | `records.load_run` | `{patient: record}` |
| 2. Load the annotations | Read every patient's annotation | `annotations/<task>/` | `records.load_annotations` | `{patient: annotation}` |
| 3. Pair them up | Keep patients that have an annotation and an answer, for one field | The two lists, a field name | Your loop (see "Using it on a run") | One answer and one annotation per patient |
| 4. Check the label | Is the model's label the person's value? | `answer[field]`, `fields[field]["value"]` | `==` here; accuracy, precision and recall in OncoTrace | Right or wrong |
| 5. Check the spans | Did the quotes land on the marked places? | Marked spans, quoted spans | `score_spans` | `n_gold`, `any_hit`, `all_hit`, `hit_rate`, `mean_coverage` |
| 6. Score the confidence | Reward or penalize by confidence and right or wrong | `answer["confidence"]`, right or wrong | `confidence_score` | One number per patient |
| 7. Add up | Average over patients; count who was left out | Step 5 and 6 results | `mean_confidence_score`, your own averages | Numbers to report |
| 8. Read | Low span score: look at the case. High confidence and wrong: look at the case | The numbers | You | Cases worth a look |

### Who is left out, and why

| Left out | Why | What to report |
|---|---|---|
| A patient with no annotation | Nothing to compare with | How many |
| A patient the model did not answer (status is not `answered`) | No label, quotes or confidence | How many, and the reason (for example server error) |
| A field with no marked span (`score_spans` returns `None`) | No place to compare against | How many fields |

## What goes in

A **span** is a stretch of a report: `document`, `start` and `end`, where `start`
and `end` are character positions in that document's text.

| Input | Where it comes from |
|---|---|
| The model's label, confidence and quotes | A run folder: `runs/<run>/units/<patient>.json`, under `answer` (`answer["tumor_count"]`, `answer["confidence"]`, `answer["quotes"][field]`) |
| The person's value and marked spans | An annotation file: `annotations/<task>/<patient>.json`, under `fields[field]` (`value` and `spans`) |

`oncotrace_bench.records.load_run` and `load_annotations` read these.

## How each score is worked out

### Span scores

For one field of one patient, take the spans the person marked (`marked`) and
the spans the model quoted (`quoted`).

1. **Overlap.** Two spans overlap by the number of characters they share. Spans
   in different documents share nothing. This is `records.overlap`, so the repo
   has one definition of overlap.
2. **`span_hit(marked_span, quoted)`.** Yes if any quote shares at least one
   character with the marked span.
3. **`span_coverage(marked_span, quoted)`.** The fraction of the marked span that
   the quotes cover. Quotes that overlap each other count once (this is
   `records.covered_fraction`):

   ```
   coverage = characters of the marked span that any quote covers
              ─────────────────────────────────────────────────────
                      length of the marked span
   ```
4. **`score_spans(marked, quoted)`.** Do steps 2 and 3 for every marked span, then
   summarize:

   | Result | How it is worked out |
   |---|---|
   | `n_gold` | Number of marked spans |
   | `any_hit` | At least one marked span was hit |
   | `all_hit` | Every marked span was hit |
   | `hit_rate` | Marked spans hit, divided by `n_gold` |
   | `mean_coverage` | Average of the coverage over the marked spans |

   It returns `None` when there is no marked span, so the field is skipped.

A worked example. The person marked two places, `100-200` and `500-600`. The model
quoted `90-150` and `700-800`.

| Marked span | Hit? | Coverage |
|---|---|---|
| 100-200 | yes (the quote 90-150 shares 100-150) | 50 of 100 characters = 0.5 |
| 500-600 | no (700-800 is elsewhere) | 0 |

So `any_hit` is true, `all_hit` is false, `hit_rate` is 0.5 and `mean_coverage` is
0.25.

### Confidence score

`confidence_score(confidence, correct)` looks up one cell of a table:

| Confidence | Label correct | Label wrong |
|---|---|---|
| high | +2 | -2 |
| medium | +1.5 | -1.5 |
| low | +1 | -1 |

`mean_confidence_score(answers)` averages the scores over a list of
`(confidence, correct)` pairs and returns `None` for an empty list. "Correct"
means the model's label equals the person's value.

## Why it is built this way

| Choice | Reason |
|---|---|
| Reuse `records.overlap` and `records.covered_fraction` | One definition of overlap in the repo, nothing to keep in step |
| Character positions, not words | Positions in OncoTrace and in annotations are characters. Counting words would need the report text and a rule for splitting it |
| Report `any_hit` and `all_hit` together | The same fact can appear twice in a report, and an answer can need two sentences together. The annotation cannot say which, so the truth is between the lenient and the strict number |
| Score each marked span, then average | Each marked place counts the same, long or short |
| Skip fields with no marked span and patients with no answer | There is nothing to compare, or no confidence to judge |
| The confidence table is a parameter | Medium confidence was not in the original proposal, so the values are a choice that can change without touching the code |

## Using it on a run

There is no script that does this for you yet. This is how to do it by hand. The
field name and folders below are examples; use the field and folders of your own
task.

```python
from pathlib import Path

from oncotrace_bench.metrics import mean_confidence_score, score_spans
from oncotrace_bench.records import load_annotations, load_run

run = load_run(Path("runs/<your run folder>"))
annotations = load_annotations(Path("annotations/<your task folder>"))
field = "myometrial_invasion"  # the field you want to score

pairs = []
for patient, record in run.items():
    answer = record["answer"]
    if answer.get("status") != "answered" or patient not in annotations:
        continue
    marked = annotations[patient]["fields"][field]
    quoted = answer["quotes"].get(field, [])
    print(patient, score_spans(marked["spans"], quoted))
    pairs.append((answer["confidence"], answer[field] == marked["value"]))

print(mean_confidence_score(pairs))
```

Only patient IDs and numbers come out, so the result is safe to share. A run
folder and annotations hold report excerpts, so keep them out of Git.

## Limits to keep in mind

- **Span scores are approximate.** If the same fact is in the report twice and the
  model quotes the other copy, it scores as a miss. A low score means "look at
  this case", not "the model is wrong".
- **`mean_coverage` does not penalize a long quote.** Quoting a whole report covers
  every marked span. A second number, the share of the quote that is useful, is
  not added yet.
- **A confidence score needs an answer.** Patients with no answer (for example a
  server error) are left out, so report how many were left out.

## Tests

`tests/test_metrics.py` has 14 tests on small hand-made spans. Run them with:

```bash
python3 -m pytest tests/test_metrics.py
```

They read no report, run folder or annotation. The repo's lint rules
(`ruff check`, `ruff format --check`) pass on both files.

## Not done yet

- A script that applies these to a run and writes tables, with a provenance
  record.
- Model runs on patients that have annotated spans (the annotations that exist
  are for the invasion task).
- Putting the metrics into OncoTrace's scoring function and TraceView, if its
  maintainers want that.
