"""Record what a result folder was made from, so it can be remade later.

Any experiment can call `build()` and save the result as `provenance.json` next
to its outputs. It records the clinic-repo commit (and any uncommitted files),
the input files with their SHA-256, and, for each OncoTrace run read, the
OncoTrace commit, task contract and config that made it.

Two rules decide where a fact comes from:

- Facts about a **run** come from what OncoTrace wrote into the run folder. They
  were fixed when the job ran, days before the analysis, so never read them from
  whatever checkout happens to be open now.
- A checkout the analysis **imports code from** is an input of the analysis. Pass
  it as `analysis_repos` so it is recorded separately, never as the run's commit.

`check()` lists the problems in a finished record; `scripts/check_provenance.py`
is the command that runs it.
"""

import hashlib
import json
import platform
import shutil
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

# Keys OncoTrace writes into a run's own provenance.json that describe the run.
# `timings` is pulled apart below; the whole record is kept under "raw" as well,
# so a field OncoTrace adds later is never silently dropped.
# "commit" is deliberately not here: the authoritative OncoTrace commit is
# `oncotrace_commits`, read from the unit records, which also covers a partial
# run. The run-level copy stays available under "raw".
RUN_KEYS = (
    "config_sha256",
    "contracts",
    "label_counts",
    "label_field",
    "labels_sha256",
    "mode",
    "model",
    "schema_version",
    "task",
    "temperature",
    "unit_count",
)


def _git(repo: Path, *args: str) -> str:
    """Run one read-only git command in `repo` and return its output, or ''."""
    git = shutil.which("git")
    if git is None or not repo.is_dir():
        return ""
    done = subprocess.run(  # noqa: S603 - fixed read-only git arguments, no user input
        [git, "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    # rstrip only: `git status --porcelain` lines start with a significant space.
    return done.stdout.rstrip() if done.returncode == 0 else ""


def repo_state(repo: Path) -> dict:
    """The commit, branch, and uncommitted files of a git checkout."""
    changed = _git(repo, "status", "--porcelain").splitlines()
    return {
        "path": str(repo),
        "commit": _git(repo, "rev-parse", "HEAD"),
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "uncommitted_files": [line[3:] for line in changed],
    }


def sha256(path: Path) -> str:
    """The SHA-256 of a file, to show which version of an input was used."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group_readable(path: Path) -> bool:
    """Whether the group can read `path` (and enter it, if it is a folder)."""
    if not path.exists():
        return False
    mode = path.stat().st_mode
    if path.is_dir():
        return bool(mode & stat.S_IRGRP and mode & stat.S_IXGRP)
    return bool(mode & stat.S_IRGRP)


def model_root(config_path: Path) -> str:
    """The weights folder a run served, from its config, or '' if not named.

    The config's SHA-256 already pins this, but the path is what tells a reader
    which checkpoint produced the answers, so it is recorded on its own too.
    """
    config = yaml.safe_load(config_path.read_text()) or {}
    serving = config.get("serving") or {}
    return str(serving.get("model_root") or "")


def server_starts(run_dir: Path) -> list[dict]:
    """Every Slurm allocation that left a log in a run folder.

    A run's own provenance names only the last job. A run whose first server
    died, or that was resumed on another node, left earlier logs behind, and
    those repeats may not mean what a reader assumes. This finds all of them.
    """
    starts: dict[str, dict] = {}
    logs = sorted(run_dir.glob("job-*.out")) + sorted(run_dir.glob("server-*.log"))
    for path in logs:
        pieces = path.stem.split("-")
        job = next((piece for piece in pieces if piece.isdigit()), "")
        if not job:
            continue
        start = starts.setdefault(job, {"job_id": job, "logs": [], "failed": False})
        start["logs"].append(path.name)
        start["failed"] = start["failed"] or "failed" in pieces
    return [starts[job] for job in sorted(starts)]


def run_state(run_dir: Path) -> dict:
    """What OncoTrace recorded about how a run was made.

    Every unit record names the OncoTrace commit and task-contract digest that
    wrote it, so the commit, digest and `package_modified` flag here cover a run
    that was stopped early. The run's own `provenance.json`, `endpoint.json` and
    `run_config.yaml` are only there for a finished run; everything they hold is
    kept, including the whole run provenance under "raw".
    """
    records = [
        json.loads(path.read_text()) for path in sorted(run_dir.glob("units/*.json"))
    ]
    contracts = [record.get("contract") or {} for record in records]
    state = {
        "path": str(run_dir),
        "records": len(records),
        "oncotrace_commits": sorted({c.get("commit") or "" for c in contracts}),
        "contract_digests": sorted({c.get("digest") or "" for c in contracts}),
        "oncotrace_modified": any(c.get("package_modified") for c in contracts),
    }
    finished = run_dir / "provenance.json"
    if finished.exists():
        made = json.loads(finished.read_text())
        for key in RUN_KEYS:
            state[key] = made.get(key)
        timings = made.get("timings") or {}
        state["job_id"] = timings.get("job_id")
        state["node"] = timings.get("node")
        state["seconds_per_unit"] = timings.get("seconds_per_unit")
        state["raw"] = made
    endpoint = run_dir / "endpoint.json"
    if endpoint.exists():
        state["endpoint"] = json.loads(endpoint.read_text())
    config = run_dir / "run_config.yaml"
    if config.exists():
        state["run_config_sha256"] = sha256(config)
        state["model_root"] = model_root(config)
    state["server_starts"] = server_starts(run_dir)
    state["group_readable"] = group_readable(run_dir)
    return state


def build(
    inputs: dict,
    runs: dict,
    repo_root: Path,
    task: Path | None = None,
    analysis_repos: dict | None = None,
    **extra: object,
) -> dict:
    """Assemble the provenance record for one experiment run.

    Args:
        inputs: name -> input file. Each is hashed.
        runs: name -> OncoTrace run folder. Each is read with `run_state`.
        repo_root: this clinic-repo checkout, where the analysis code lives.
        task: the task contract YAML, if the experiment used one. Hashed so the
            record ties to a committed file as well as to the digest in the
            records.
        analysis_repos: name -> a checkout the analysis imports code from (an
            OncoTrace clone it reads `viewer/` from, say). Recorded as an input
            of the analysis, never as the commit that made a run.
        **extra: anything else (counts, arguments) is stored as given.

    Returns:
        The record to write as `provenance.json` next to the outputs.
    """
    record = {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "clinic_repo": repo_state(repo_root),
        "inputs": {
            name: {"path": str(path), "sha256": sha256(Path(path))}
            for name, path in inputs.items()
        },
        "runs": {name: run_state(Path(path)) for name, path in runs.items()},
    }
    if task is not None:
        # Same two keys #11 used, so records from either side read the same way.
        record["task"] = str(task)
        record["task_sha256"] = sha256(Path(task))
    if analysis_repos:
        record["analysis_repos"] = {
            name: repo_state(Path(path)) for name, path in analysis_repos.items()
        }
    return {**record, **extra}


def check(record: dict) -> list[str]:
    """The problems in a finished provenance record, as sentences.

    These are the checks a reviewer would otherwise do by hand. Whether a commit
    exists on GitHub needs the network, so `scripts/check_provenance.py` does
    that part.

    Args:
        record: a loaded `provenance.json`.

    Returns:
        One sentence per problem; empty if the record is clean.
    """
    problems = []
    clinic = record.get("clinic_repo") or {}
    if not clinic.get("commit"):
        problems.append("clinic_repo.commit is empty: git did not answer")
    for name in clinic.get("uncommitted_files") or []:
        problems.append(f"clinic_repo was dirty: {name} was not committed")
    for name, repo in (record.get("analysis_repos") or {}).items():
        for changed in repo.get("uncommitted_files") or []:
            problems.append(f"analysis repo {name} was dirty: {changed}")
    if not record.get("runs"):
        problems.append(
            "no runs recorded: this record cannot say which OncoTrace commit or "
            "contract produced the answers. Use provenance.build(runs=...)"
        )
    for name, run in (record.get("runs") or {}).items():
        commits = [value for value in run.get("oncotrace_commits") or [] if value]
        digests = [value for value in run.get("contract_digests") or [] if value]
        if len(commits) != 1:
            problems.append(f"run {name} names {len(commits)} OncoTrace commits, not 1")
        if len(digests) != 1:
            problems.append(f"run {name} names {len(digests)} contract digests, not 1")
        if run.get("oncotrace_modified"):
            problems.append(f"run {name} ran a modified OncoTrace package")
        if not Path(run.get("path", "")).exists():
            problems.append(f"run {name} is gone: {run.get('path')}")
        elif not run.get("group_readable", True):
            problems.append(f"run {name} is not group-readable: {run.get('path')}")
        starts = run.get("server_starts") or []
        if len(starts) > 1:
            jobs = ", ".join(start["job_id"] for start in starts)
            problems.append(
                f"run {name} spans {len(starts)} server starts ({jobs}); its own "
                "provenance names only the last. Say so in the README."
            )
    return problems
