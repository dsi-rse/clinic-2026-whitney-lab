# Whitney Lab clinical extraction benchmark

Evaluate how reliably [OncoTrace](https://github.com/uchicago-dsi/oncotrace)
extracts clinical labels from pathology reports, whether its citations support
those labels, and what retrieval adds compared with reading the whole record.
We start with TCGA endometrial cancer reports; RadGraph is a possible additional
dataset later in the quarter.

## Getting started

1. Follow [student setup](docs/student-setup.md) for Claude Code, both skills
   collections, and one Python 3.12 environment for analysis and the OncoTrace client.
   Follow the [clinic Python guidelines](docs/PYTHON_DEVELOPMENT_GUIDELINES.md)
   and set `DATA_DIR` in your ignored `.env`.
2. Follow [OncoTrace's synthetic first-run recipe](https://github.com/uchicago-dsi/oncotrace#getting-started),
   reusing that client environment. Each student runs the smoke test and inspects
   their own three patient records in [TraceView](docs/student-setup.md#run-traceview).
   Use the [shared weights](docs/student-setup.md#shared-model-weights) when serving;
   check access from your own account.
3. Use [config/endometrial.yaml](config/endometrial.yaml) for your endometrial run.
   It points to the [shared report store and roster](docs/student-setup.md#shared-endometrial-data),
   readable by `__oncotrace`, and attaches to the lab's GLM-5.3-Flash server.
   If the cluster is unavailable, build the same data on your own machine with
   [local data](docs/local-data.md).
   Update the input paths in older personal configs and obtain the active server's
   endpoint/job details from the mentor. Follow [OncoTrace's running guide](https://github.com/uchicago-dsi/oncotrace/blob/main/docs/running.md)
   for validation, running on the server's compute node, and producing outputs.
4. Give your run its own output directory. Check progress against the roster;
   546 records can include unanswered cases. Start analysis while the run proceeds.

The clinic config has no serving block: use an existing endpoint rather than
`--serve`. A different model or dataset path requires a personal config.

## Running on OpenRouter

Use this on your laptop, or whenever the cluster is down. OpenRouter is a paid
service that hosts GLM-5.3-Flash, the model the cluster runs, so no GPU is
needed. The TCGA reports are public, so sending them there is allowed.

1. Build the data once: `bash scripts/endometrial_data/download.sh`
   (see [local data](docs/local-data.md)).
2. Your mentor sends you your own OpenRouter key. Copy `.env.example` to `.env`,
   paste the key after `OPENROUTER_API_KEY=`, run `chmod 600 .env`, and delete
   the message that carried the key. Never commit the key or post it anywhere.
3. Get an OncoTrace clone at its current `main` (it has to include the
   `endpoint` setting) and a Python environment with `httpx`, `pydantic` and
   `pyyaml`, as in OncoTrace's `envs/oncotrace-client.yml`.
4. From this repo's root:

   ```bash
   set -a; source .env; set +a
   PYTHONPATH=~/oncotrace python -m oncotrace.runner extract \
     --config config/endometrial_openrouter.yaml \
     --output runs/<YYYY-MM-DD>_<experiment>_<arm>
   ```

   For a quick try, copy the config and point its `roster` at a CSV with a
   `unit` column listing a few patients.

[config/endometrial_openrouter.yaml](config/endometrial_openrouter.yaml) is
[config/endometrial.yaml](config/endometrial.yaml) with the changes marked
`CHANGED`: the local data paths, OpenRouter's address and key variable, its name
for the model, and one pinned provider. Every request goes to that one provider
so all answers come from the same copy of the model; each unit record names the
provider that answered. A 50-patient agentic run costs about $0.15 there:
the token counts per patient in
[the full-cohort baseline](experiments/endometrial_agentic_vs_one_shot/results/baseline/totals.csv)
times the provider's price on 16 November 2026.

Results from OpenRouter are not the same as results from the cluster: the
provider runs its own compressed copy of the model on its own software. Say
which one you used when you compare runs. Run folders stay on your machine, out
of Git (`runs/` is ignored); copy them to the shared workspace when the cluster
is back (see "Reproducibility" in [AGENTS.md](AGENTS.md)).

## Endometrial starting point

[Mariam Hassan](https://github.com/marihassan) developed the initial adaptation
and annotated 50 patients. Her authorship is preserved in the imported Git history.
See [the import record](docs/endometrial-data.md) for source commits, input paths,
and reference limitations.

| Artifact | Location |
|---|---|
| Myometrial-invasion task | [tasks/endo_myometrial_invasion.yaml](tasks/endo_myometrial_invasion.yaml) |
| Protocol definitions | [CAP mapping](docs/cap-mapping.md) |
| Reference annotations | [annotations/endo_myometrial_invasion/](annotations/endo_myometrial_invasion/) |
| Run config | [config/endometrial.yaml](config/endometrial.yaml) |

Reports and run outputs stay outside Git. Annotations contain saved evidence
excerpts from the TCGA reports. These 50 medical-student annotations are a
reference for development, with 45 from one tissue source site; they are not an
independently adjudicated test set. Keep invasion, depth, clinical indeterminacy,
and pipeline noncompletion separate in evaluation.

## Scoring spans and confidence

OncoTrace already scores an answer's **label** against a person's annotation
(accuracy, precision and recall; see `oncotrace.score`). Two other checks live
in [src/oncotrace_bench/metrics.py](src/oncotrace_bench/metrics.py):

- **Did the model quote the right place in the report?** (span scores)
- **Was the model sure when it was right, and unsure when it was wrong?**
  (confidence score)

These are small helper functions. They read no report text: they work on
character positions, labels and confidence levels only.

### All the metrics at a glance

Three kinds of check, each answering a different question. An answer can have the
right label and still quote the wrong place, which is worth a look.

| Kind | Metric | Question it answers | How it is worked out | Where it is computed |
|---|---|---|---|---|
| Label | Accuracy | How many labels are right? | Right answers divided by all patients | OncoTrace (`oncotrace.score`) |
| Label | Precision | When the model says "this class", how often is it? | Per class: right divided by all the model put in that class | OncoTrace |
| Label | Recall | Of the patients really in a class, how many did the model find? | Per class: right divided by all a person put in that class | OncoTrace |
| Span | `any_hit` | Did the model quote any place the person marked? | A quote overlaps at least one marked span: yes or no | `metrics.py` |
| Span | `all_hit` | Did it quote every place the person marked? | Quotes overlap every marked span: yes or no | `metrics.py` |
| Span | `hit_rate` | How many of the marked places did it quote? | Marked spans quoted divided by all marked spans | `metrics.py` |
| Span | `mean_coverage` | How much of each marked stretch do the quotes cover? | Shared length divided by the marked span's length, averaged | `metrics.py` |
| Confidence | Reward or penalty | Was the model sure when it was right, and unsure when it was wrong? | Confident and right scores most; confident and wrong scores least | `metrics.py` |

The sections below explain the span and confidence rows, and what each can and
cannot tell you.

### Span scores

A *span* is a stretch of a report, written as `document`, `start` and `end`
(character positions). OncoTrace writes the spans the model quoted in each
answer, and each annotation holds the spans a person marked.

`score_spans(annotated_spans, model_spans)` compares them for one field of one
patient:

| Result | What it means |
|---|---|
| `n_gold` | How many places the person marked. |
| `any_hit` | The model quoted at least one place the person marked. The lenient check. |
| `all_hit` | The model quoted every place the person marked. The strict check. |
| `hit_rate` | The share of marked places the model quoted. |
| `mean_coverage` | On average, how much of each marked stretch the model's quotes cover (0 to 1). |

```python
from oncotrace_bench.metrics import score_spans

marked = [
    {"document": "d1", "start": 100, "end": 200},
    {"document": "d1", "start": 500, "end": 600},
]
quoted = [
    {"document": "d1", "start": 90, "end": 150},   # covers half of the first
    {"document": "d1", "start": 700, "end": 800},  # near neither
]
score_spans(marked, quoted)
# {'n_gold': 2, 'any_hit': True, 'all_hit': False,
#  'hit_rate': 0.5, 'mean_coverage': 0.25}
```

**How to read it.** Look at `any_hit` and `all_hit` together; the truth is
between them. A low score means "go and look at this case", not "the model is
wrong". These scores are approximate, for three reasons:

- The same fact can appear twice in a report. If the model quotes the other
  copy, it scores as a miss.
- An answer may need two sentences together. The annotation has no way to say
  so.
- A long quote is not penalized: quoting a whole report covers every marked
  stretch.

Fields with no marked span (for example the annotation says "none stated") are
skipped; `score_spans` returns `None` for them.

### Confidence score

`confidence_score(confidence, correct)` gives a reward or a penalty for one
answer, depending on how confident the model said it was and whether its label
was right.

| Confidence | Label correct | Label wrong |
|---|---|---|
| high | +2 | -2 |
| medium | +1.5 | -1.5 |
| low | +1 | -1 |

Most rewarded is confident and right; most penalized is confident and wrong.
`mean_confidence_score` averages this over a list of `(confidence, correct)`
pairs. A patient the model did not answer has no confidence, so leave them out
and report how many you left out. The table is a parameter, so you can pass your
own.

### Choices made here

The metric set was proposed for issue #52. Where the proposal was silent, these
are the choices made:

- "Medium" confidence sits halfway between high and low.
- Positions are counted in characters, not words.
- Several marked spans are scored one by one and averaged; the model's quotes
  for the field count together.
- A field with no marked span is skipped for span scores. A patient the model did
  not answer is skipped for the confidence score.
- A long quote is not penalized.

Each can be changed later; the confidence table is a parameter.

### Not done yet

- There is no script that applies these to a run, and no result tables yet. They
  need model runs on patients that have annotated spans; the annotations here
  are for the invasion task.
- They are not part of OncoTrace or TraceView.

Run the tests with `python3 -m pytest tests/test_metrics.py`.

## Working here

Each experiment is a self-contained folder in `experiments/<name>/`. Only general
helpers that teammates can reuse go in `src/oncotrace_bench/`; other command-line
scripts go in `scripts/`, and short exploratory notebooks in `notebooks/`. Keep code readable,
review it with the TA or mentor, and document runnable scripts. General extraction
improvements belong in OncoTrace; dataset-specific analysis belongs here.

Every result folder records what made it, as `provenance.json` written by
`oncotrace_bench.provenance.build()`. Before opening a PR, run
`make check-provenance` ([scripts/check_provenance.py](scripts/check_provenance.py))
to check those records. See "Experiments and provenance" in
[AGENTS.md](AGENTS.md).

Read [AGENTS.md](AGENTS.md) before using a coding agent. Copy
`agents.local.example.md` to ignored `agents.local.md` for personal preferences.
Student-written code requires permission before an agent changes it.

Experiments live in [experiments/](experiments/). Start with
[endometrial_failure_modes](experiments/endometrial_failure_modes/README.md): why OncoTrace
sometimes gives no answer, and whether its confidence tells us anything.
