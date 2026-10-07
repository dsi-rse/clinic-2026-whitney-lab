# Student coding-agent setup

Use your own cluster account and the mentor/course-provided Claude account or
approved billing arrangement. Never share credentials. Install the coding agent
and skills once per account; OncoTrace's model/environment is a separate setup.

## Claude Code

Follow the [official Linux installation guide](https://code.claude.com/docs/en/setup)
and [authentication instructions](https://code.claude.com/docs/en/authentication).
The native installer is:

```bash
curl -fsSL https://claude.ai/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
claude --version
claude doctor
claude
```

This installs into your account: `~/.local/bin/claude` points to a binary under
`~/.local/share/claude/versions/`. It needs neither sudo nor a micromamba
environment. Keep `~/.local/bin` on your PATH in new shells. Claude can then
use whichever Python environment you activate for the project.

Follow cluster policy for installation resources. Authentication may require a
browser on your laptop. Record the installed version and demonstrate a working
session, without saving tokens or login codes in project notes.

## Global skills

Install both collections globally for Claude Code. These commands are for a
fresh installation; reuse an existing clone and inspect existing skill folders
before copying over customizations.

```bash
git clone https://github.com/dsi-rse/skills.git ~/dsi-rse-skills
git clone https://github.com/uchicago-dsi/ai-sci-skills.git ~/ai-sci-skills
mkdir -p ~/.claude/skills
cp -R ~/dsi-rse-skills/skills/clinic/* ~/.claude/skills/
cp -R ~/dsi-rse-skills/skills/engineering/* ~/.claude/skills/
cp -R ~/ai-sci-skills/skills/* ~/.claude/skills/
git -C ~/dsi-rse-skills rev-parse HEAD
git -C ~/ai-sci-skills rev-parse HEAD
```

Codex users can copy the same directories into `~/.codex/skills/` after creating
it. Open a fresh agent session if it caches available skills and demonstrate one
skill is discoverable. The [DSI RSE README](https://github.com/dsi-rse/skills)
also describes a managed Claude plugin; the [AI Sci Skills README](https://github.com/uchicago-dsi/ai-sci-skills)
explains copies and symlinks. Record the source commits and installation method.

## Project environments

Use one **Python 3.12 student environment** for clinic analysis and the OncoTrace
client. The clinic package requires Python 3.12 or newer; OncoTrace supports
Python 3.11 or newer. A separate clinic environment is optional. The lightweight
OncoTrace example pins Python 3.11, so that unchanged example cannot install the
clinic package.

Inside a CPU Slurm allocation, set `WORKSPACE` to your own approved storage path
and run these commands from the clinic repo root:

```bash
export WORKSPACE=/path/to/approved/storage
export MAMBA_ROOT_PREFIX="$WORKSPACE/micromamba"
export CLIENT="$WORKSPACE/envs/clinic-client"
micromamba create -y -p "$CLIENT" -c conda-forge \
  python=3.12 pip httpx 'pydantic>=2' pyyaml
"$CLIENT/bin/python" -m pip install -e .
"$CLIENT/bin/python" -c 'import httpx, pydantic, yaml, numpy, pandas; print("client and analysis imports ok")'
```

Follow the [clinic Python guidelines](PYTHON_DEVELOPMENT_GUIDELINES.md) for
development tools and set `DATA_DIR` in ignored `.env`. Use the same interpreter
for analysis scripts or register it as your notebook kernel.

Follow [OncoTrace's getting-started recipe](https://github.com/uchicago-dsi/oncotrace#getting-started)
for your synthetic extraction, keeping `CLIENT` set to this environment and
skipping its environment-creation step. Set `PYTHONPATH` to the OncoTrace clone
as directed there. See [OncoTrace's environment guidance](https://github.com/uchicago-dsi/oncotrace/blob/main/docs/first-run.md#client-and-serving-environments)
for reusing an analysis environment.

The **GPU serving environment remains separate**; use the lab's established
server rather than installing vLLM into the student environment. Follow your
site's Slurm rules for builds and inference. Use your own output directories and
review the agent's commands and code. Read the shared repo instructions before starting;
keep personal preferences in ignored `agents.local.md`.

## Shared model weights

Use the shared checkpoints in the OncoTrace project space rather than
downloading a copy per student. `READY.json` beside them records verification
and current locations.

| Use | Model | Shared path |
|---|---|---|
| Synthetic smoke example | Qwen3-30B-A3B-Instruct-2507 | `/net/spaces/annawoodard/oncotrace/weights/Qwen3-30B-A3B-Instruct-2507` |
| Endometrial run | GLM-5.3-Flash | `/net/spaces/annawoodard/oncotrace/weights/GLM-5.3-Flash-stripe8` |

Project access requires `__oncotrace` (GID `4000004`). The checkpoints are
read-only for this group. If you were recently added, reconnect SSH/VS Code
and check `id` in the new session. Retained `__karczmar` ACLs on the weights
do not grant traversal through the root-owned project directory; ask Anna
about missing project membership rather than changing permissions yourself.
From your own account, confirm you can read each model's `config.json` and
`model.safetensors.index.json`. Report a permission error to Anna before proceeding.
All 100 copied files matched the originals by SHA-256 on October 7, 2026,
including 16 Qwen shards and 62 GLM shards. Original verification manifests
are in `weights/transfer/`; `weights/relocation/` records the verified move.
The `-stripe8` suffix is part of the GLM path.

The original checkpoints remain under
`/net/spaces/annawoodard/annawoodard/oncotrace-dsi/weights/`, with their existing
`annawoodard` group permissions. Transfer and relocation records accompany the
project copies; use the project paths above in personal serving configs.

When attaching to the lab's server, use its endpoint and served model name;
the server owns the weights path. If you are starting an approved personal
server, set `serving.model_root` to the appropriate shared path, following the
[DSI serving instructions](https://github.com/uchicago-dsi/oncotrace/blob/main/docs/dsi-cluster.md#setting-up-as-a-new-student).
Keep your caches and sockets in your own account's paths. The clinic endometrial
config attaches to GLM; changing models requires a matched personal config.

## Run TraceView

Every student starts TraceView and opens their own synthetic smoke run.
Follow [TraceView's read-only launch recipe](https://github.com/uchicago-dsi/oncotrace/blob/main/viewer/README.md#read-only-review-on-a-cluster)
using the student/client interpreter. Forward the port in your own VS Code
session and inspect the three patients' labels, source passages, and tool traces.
Then open your endometrial run with the clinic's
`tasks/endo_myometrial_invasion.yaml` contract, rather than its run config.

Use read-only mode for these tasks. Inspect inherited annotations separately
in your clinic checkout; do not edit Mariam's references. TraceView's automated
view can inspect runs as they produce completed records. A working launch means
you can open a patient and its source/trace, rather than only seeing a server URL.

## Talk through OncoTrace with your agent

After your smoke test, spend 20–30 minutes asking your agent how OncoTrace works.
Have it read the README and inspect the existing open-source implementation and
synthetic examples. Open your own run in TraceView and use its source and
trajectory views for the conversation. Ask follow-up questions until you can
walk through one patient's extraction yourself. Check one explanation against
the code or trace.

For the meeting, be ready to explain what the system returns, what a task contract
defines, what inventory/search/read/submit do, how citations are checked, how
agentic and one-shot differ, and why an indeterminate clinical answer differs
from no accepted submission. Bring one question or correction. Explain in your
own words rather than reading the agent's answer.
