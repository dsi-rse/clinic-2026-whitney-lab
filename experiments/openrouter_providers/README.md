# Which OpenRouter provider of GLM-5.3-Flash to use

OpenRouter forwards each request to one of several companies ("providers") that
host GLM-5.3-Flash, each with its own copy of the model, often compressed to 4 or
8 bits per weight. Students running on OpenRouter need one provider pinned, so
that every answer comes from the same copy. This experiment asks which provider
to pin: does the choice change OncoTrace's answers on the endometrial task, and
does any provider fail to run it?

## Design

- **Patients:** the 10 of `../endometrial_determinism/roster_followup10.csv`,
  which the cluster ran 20 times each.
- **Arms:** one provider each, 3 repeats per arm. The configs in `configs/` are
  identical except for the provider line, and match
  `config/endometrial_openrouter.yaml` except for the roster.

  | Arm | Provider | Weights |
  | --- | --- | --- |
  | `wafer_us` | `wafer/us` | 4-bit (nvfp4) |
  | `darkbloom_fp4` | `darkbloom/fp4` | 4-bit (fp4) |
  | `open_inference_fp4` | `open-inference/fp4` | 4-bit (fp4) |
  | `morph_fp8` | `morph/fp8` | 8-bit (fp8) |

  Every provider was chosen because it supports `tool_choice: required`, which
  OncoTrace sends on every request until the model has answered; 27 of the 42
  GLM-5.3-Flash providers on OpenRouter supported it on 16 November 2026.
  `darkbloom_fp4` refused every request that day, so `open_inference_fp4`, the
  next cheapest 4-bit provider with that support, was added after it failed.
- **Reference:** the cluster's 20 repeats of the same patients
  (`../endometrial_determinism/results/2026-11-02_095348_agentic_0b6f404_10x20/per_patient.csv`).
  Those ran under the task contract from before PR 48, so they show how much the
  cluster's answers vary, not what the cluster would answer today.

## Rerun

The extraction calls a paid service and its answers vary from run to run, so it
cannot be reproduced exactly; the run folders are kept instead (below). From a
fresh clone, with OncoTrace at branch `openrouter-endpoint` or later, the data
built by `scripts/endometrial_data/download.sh`, and `OPENROUTER_API_KEY` set:

```bash
set -a; source .env; set +a
RUNS=runs ONCOTRACE_REPO=~/oncotrace PYTHON=python \
  ARMS="wafer_us darkbloom_fp4 morph_fp8 open_inference_fp4" \
  bash experiments/openrouter_providers/run_providers.sh
```

About 30 minutes; each arm runs its 3 repeats one after another, the arms side
by side. Under $1 at November 2026 prices.

The tables are remade exactly from the run folders, in a few seconds, by passing
the saved price list:

```bash
PYTHONPATH=src python experiments/openrouter_providers/compare_providers.py \
  --arm wafer_us=runs/2026-11-16_openrouter_providers_wafer_us \
  --arm darkbloom_fp4=runs/2026-11-16_openrouter_providers_darkbloom_fp4 \
  --arm open_inference_fp4=runs/2026-11-16_openrouter_providers_open_inference_fp4 \
  --arm morph_fp8=runs/2026-11-16_openrouter_providers_morph_fp8 \
  --prices experiments/openrouter_providers/results/<folder>/prices.csv \
  --not-shared "<where the run folders are>"
```

Without `--prices` it fetches today's prices, so `cost_usd` changes.

## Run folders

The DSI cluster was down, so the 12 run folders were made on CRI, under
`/gpfs/data/huo-lab/Image/annawoodard/clinic-2026-whitney-lab/runs/2026-11-16_openrouter_providers_<arm>/rep1..3`.
Students cannot read CRI. They will be copied to
`/net/spaces/annawoodard/oncotrace/workspaces/annawoodard/runs/` when the
cluster is back; `provenance.json` acknowledges this for each run.
