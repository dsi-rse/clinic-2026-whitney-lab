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
   It points to the existing shared report store and roster, and attaches to the
   lab's GLM-5.3-Flash server. Check input access and obtain the active server's
   endpoint/job details from the mentor. Follow [OncoTrace's running guide](https://github.com/uchicago-dsi/oncotrace/blob/main/docs/running.md)
   for validation, running on the server's compute node, and producing outputs.
4. Give your run its own output directory. Check progress against the roster;
   546 records can include unanswered cases. Start analysis while the run proceeds.

The clinic config has no serving block: use an existing endpoint rather than
`--serve`. A different model or dataset path requires a personal config.

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

Reusable analysis code goes in `src/oncotrace_bench/`, command-line scripts in
`scripts/`, and short exploratory notebooks in `notebooks/`. Keep code readable,
review it with the TA or mentor, and document runnable scripts. General extraction
improvements belong in OncoTrace; dataset-specific analysis belongs here.

Read [AGENTS.md](AGENTS.md) before using a coding agent. Copy
`agents.local.example.md` to ignored `agents.local.md` for personal preferences.
Student-written code requires permission before an agent changes it.
