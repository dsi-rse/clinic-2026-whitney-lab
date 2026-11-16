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
