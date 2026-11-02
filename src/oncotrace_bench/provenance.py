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

import grp
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
# "commit" is deliberately not among them: the authoritative OncoTrace commit is
# `oncotrace_commits`, read from the unit records, which also covers a partial
# run. The whole run record is kept under "raw", and `check()` compares the two.
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

# What a job log says when its server came up, and when it never did. A server
# that never published an endpoint served no units, so it is not a second
# attempt at the work: it is a failed start, which is worth recording but is not
# a problem with the result.
ENDPOINT_MARKERS = ("endpoint ready", "endpoint published")


def _git(repo: Path, *args: str) -> tuple[bool, str]:
    """Run one read-only git command in `repo`.

    Returns:
        `(True, output)`, or `(False, why it failed)`. A failure is never
        returned as an empty answer, because "" and "git refused" would then
        look the same in a provenance record.
    """
    git = shutil.which("git")
    if git is None:
        return False, "git is not installed"
    if not repo.is_dir():
        return False, f"{repo} is not a folder"
    done = subprocess.run(  # noqa: S603 - fixed read-only git arguments, no user input
        [git, "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        why = (done.stderr or done.stdout).strip()
        return False, why or f"git {args[0]} exited {done.returncode}"
    # rstrip only: `git status --porcelain` lines start with a significant space.
    return True, done.stdout.rstrip()


def remote_slug(url: str) -> str:
    """The 'owner/name' in a git remote URL, or '' if there is none."""
    url = url.strip().removesuffix(".git")
    if not url:
        return ""
    pieces = [piece for piece in url.replace(":", "/").split("/") if piece]
    return "/".join(pieces[-2:]) if len(pieces) >= 2 else ""  # noqa: PLR2004


def repo_state(repo: Path) -> dict:
    """The commit, branch, remote, and uncommitted files of a git checkout.

    If git cannot answer, the record says so in an `error` field rather than
    reporting a clean checkout at no commit.
    """
    answers = {
        "commit": _git(repo, "rev-parse", "HEAD"),
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "status": _git(repo, "status", "--porcelain"),
    }
    ok_remote, remote = _git(repo, "remote", "get-url", "origin")
    changed = answers["status"][1].splitlines() if answers["status"][0] else []
    state = {
        "path": str(repo),
        "commit": answers["commit"][1] if answers["commit"][0] else "",
        "branch": answers["branch"][1] if answers["branch"][0] else "",
        "remote": remote_slug(remote) if ok_remote else "",
        "uncommitted_files": [line[3:] for line in changed],
    }
    failures = [why for ok, why in answers.values() if not ok]
    if failures:
        state["error"] = "; ".join(dict.fromkeys(failures))
    return state


def sha256(path: Path) -> str:
    """The SHA-256 of a file, to show which version of an input was used."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group_access(path: Path) -> dict:
    """Whether the group can reach `path`, and the group of every folder above it.

    A run folder with group permissions of its own is still unreachable if a
    folder above it is private, so this walks the whole path. It is the same
    thing `namei -l` shows, which `## Reproducibility` item 1 asks people to
    check by hand.

    Returns:
        `{"reachable": bool, "chain": [{"path", "group", "group_ok"} ...]}`. The
        chain stops at the first folder that cannot be read at all.
    """
    chain: list[dict] = []
    reachable = True
    for part in reversed([path, *path.parents]):
        try:
            info = part.stat()
        except OSError as problem:
            chain.append({"path": str(part), "error": problem.strerror or "unreadable"})
            return {"reachable": False, "chain": chain}
        try:
            group = grp.getgrgid(info.st_gid).gr_name
        except (KeyError, OverflowError):
            group = str(info.st_gid)
        needed = stat.S_IXGRP | (stat.S_IRGRP if part == path else 0)
        group_ok = info.st_mode & needed == needed
        chain.append({"path": str(part), "group": group, "group_ok": group_ok})
        reachable = reachable and group_ok
    return {"reachable": reachable, "chain": chain}


def model_root(config_path: Path) -> str:
    """The weights folder a run served, from its config, or '' if not named.

    The config's SHA-256 already pins this, but the path is what tells a reader
    which checkpoint produced the answers, so it is recorded on its own too.
    """
    config = yaml.safe_load(config_path.read_text()) or {}
    serving = config.get("serving") or {}
    return str(serving.get("model_root") or "")


def _job_id(path: Path) -> str:
    """The Slurm job id in a log file's name, or '' if there is none."""
    pieces = path.stem.split("-")
    return next((piece for piece in pieces if piece.isdigit()), "")


def server_starts(run_dir: Path) -> list[dict]:
    """Every Slurm allocation that left a log in a run folder.

    A run's own provenance names only the last job. `published_endpoint` says
    whether an allocation actually served: one that died during startup served
    no units, so it does not mean the run was resumed or split. A run that
    attached to another run's server has no job log here at all, and this
    returns an empty list.
    """
    starts: dict[str, dict] = {}
    for path in sorted(run_dir.glob("job-*.out")):
        job = _job_id(path)
        if not job:
            continue
        text = path.read_text(errors="replace").lower()
        starts[job] = {
            "job_id": job,
            "log": path.name,
            "published_endpoint": any(mark in text for mark in ENDPOINT_MARKERS),
        }
    for path in sorted(run_dir.glob("server-*.log")):
        job = _job_id(path)
        if job and job not in starts:
            starts[job] = {"job_id": job, "log": path.name, "published_endpoint": False}
    return [starts[job] for job in sorted(starts)]


def run_state(run_dir: Path) -> dict:
    """What OncoTrace recorded about how a run was made.

    Every unit record names the OncoTrace commit and task-contract digest that
    wrote it, so the commit, digest and `package_modified` flag here cover a run
    that was stopped early. The run's own `provenance.json`, `endpoint.json` and
    `run_config.yaml` are only there for a finished run; everything they hold is
    kept, including the whole run provenance under "raw", which `check()`
    compares against the facts read from the unit records.
    """
    records = [
        json.loads(path.read_text()) for path in sorted(run_dir.glob("units/*.json"))
    ]
    contracts = [record.get("contract") or {} for record in records]
    state = {
        "path": str(run_dir),
        "records": len(records),
        "units_without_contract": sum(1 for c in contracts if not c.get("digest")),
        "oncotrace_commits": sorted(
            {c["commit"] for c in contracts if c.get("commit")}
        ),
        "contract_digests": sorted({c["digest"] for c in contracts if c.get("digest")}),
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
    state["group_access"] = group_access(run_dir)
    return state


def build(
    inputs: dict,
    runs: dict,
    repo_root: Path,
    task: Path | None = None,
    analysis_repos: dict | None = None,
    dirty_reason: str | None = None,
    **extra: object,
) -> dict:
    """Assemble the provenance record for one experiment run.

    Call this *before* writing the output folder, or the new folder shows up as
    uncommitted in the record. `compare_temperature.py` is the example.

    Args:
        inputs: name -> input file. Each is hashed. Pass every input the result
            depends on: rosters, edit manifests, configs.
        runs: name -> OncoTrace run folder. Each is read with `run_state`.
        repo_root: this clinic-repo checkout, where the analysis code lives.
        task: the task contract YAML, if the experiment used one. Hashed so the
            record ties to a committed file as well as to the digest in the
            records.
        analysis_repos: name -> a checkout the analysis imports code from (an
            OncoTrace clone it reads `viewer/` from, say). Recorded as an input
            of the analysis, never as the commit that made a run.
        dirty_reason: why the checkout had uncommitted files, if it did. Set
            this only when the result genuinely had to be made from a dirty
            tree; `check()` then reports the reason instead of failing.
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
    if dirty_reason:
        record["dirty_reason"] = dirty_reason
    return {**record, **extra}


def _repo_problems(name: str, repo: dict, require_commit: bool) -> list[str]:
    """Problems with one recorded checkout: git failures and a missing commit."""
    problems = []
    if repo.get("error"):
        problems.append(f"{name}: git could not be read ({repo['error']})")
    elif require_commit and not repo.get("commit"):
        problems.append(f"{name}.commit is empty, so this checkout pins nothing")
    return problems


def _reach_problems(name: str, run: dict) -> list[str]:
    """Problems reaching a run folder: gone, unreadable, or not group-readable."""
    path = run.get("path")
    if not path:
        return [f"run {name} records no path"]
    try:
        there = Path(path).exists()
    except OSError as problem:
        return [f"run {name} cannot be reached: {path} ({problem.strerror})"]
    if not there:
        return [f"run {name} is gone, or is not reachable from here: {path}"]
    access = run.get("group_access") or {}
    if access and not access.get("reachable", True):
        blocked = [
            step["path"]
            for step in access.get("chain") or []
            if step.get("error") or not step.get("group_ok", True)
        ]
        where = blocked[0] if blocked else path
        return [f"run {name} is not reachable by the group: {where}"]
    return []


def _agreement_problems(name: str, run: dict) -> list[str]:
    """Where the unit records and the run's own provenance disagree."""
    raw = run.get("raw") or {}
    if not raw:
        return []
    problems = []
    commits = run.get("oncotrace_commits") or []
    if raw.get("commit") and commits and raw["commit"] not in commits:
        problems.append(
            f"run {name}: its provenance says OncoTrace {raw['commit'][:8]}, but its "
            f"unit records say {', '.join(c[:8] for c in commits)}"
        )
    digests = set(run.get("contract_digests") or [])
    declared = set(raw.get("contracts") or {})
    if declared and digests and declared != digests:
        problems.append(
            f"run {name}: its provenance and its unit records name different "
            "task contracts"
        )
    if raw.get("unit_count") is not None and run.get("records") is not None:
        if raw["unit_count"] != run["records"]:
            problems.append(
                f"run {name}: {run['records']} unit records, but its provenance "
                f"says {raw['unit_count']} units"
            )
    return problems


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
    problems += _repo_problems("clinic_repo", clinic, require_commit=True)
    dirty = clinic.get("uncommitted_files") or []
    if dirty and not record.get("dirty_reason"):
        problems += [
            f"clinic_repo was dirty: {name} was not committed. If that was "
            "unavoidable, pass dirty_reason= to build()."
            for name in dirty
        ]
    for name, repo in (record.get("analysis_repos") or {}).items():
        problems += _repo_problems(f"analysis repo {name}", repo, require_commit=True)
        problems += [
            f"analysis repo {name} was dirty: {changed}"
            for changed in repo.get("uncommitted_files") or []
        ]
    if not record.get("runs"):
        problems.append(
            'no runs recorded under "runs", so nothing here can be checked as a '
            "run. An older record may hold the same facts under other keys; "
            "remake it with provenance.build(runs=...) to have them checked"
        )
    for name, run in (record.get("runs") or {}).items():
        commits = run.get("oncotrace_commits") or []
        digests = run.get("contract_digests") or []
        if len(commits) != 1:
            problems.append(f"run {name} names {len(commits)} OncoTrace commits, not 1")
        if len(digests) != 1:
            problems.append(f"run {name} names {len(digests)} contract digests, not 1")
        missing = run.get("units_without_contract") or 0
        if missing:
            problems.append(f"run {name} has {missing} unit record(s) with no contract")
        if run.get("oncotrace_modified"):
            problems.append(f"run {name} ran a modified OncoTrace package")
        problems += _reach_problems(name, run)
        problems += _agreement_problems(name, run)
        served = [
            start
            for start in run.get("server_starts") or []
            if start.get("published_endpoint")
        ]
        if len(served) > 1:
            jobs = ", ".join(start["job_id"] for start in served)
            problems.append(
                f"run {name} was served by {len(served)} server starts ({jobs}); its "
                "own provenance names only one. Say so in the README, since the "
                "repeats may not mean what a reader assumes."
            )
    return problems
