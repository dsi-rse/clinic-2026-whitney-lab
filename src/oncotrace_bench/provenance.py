"""Record what a result folder was made from, so it can be remade later.

Any experiment can call `build()` and save the result as `provenance.json` next
to its outputs. It records the clinic-repo commit (and any uncommitted files),
the input files with their SHA-256, and, for each OncoTrace run read, the
OncoTrace commit, task contract and config that made it.
"""

import hashlib
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


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


def run_state(run_dir: Path) -> dict:
    """What OncoTrace recorded about how a run was made.

    Every unit record names the OncoTrace commit and task-contract digest that
    wrote it, so this works for a run that was stopped early. The run's own
    `provenance.json` and `run_config.yaml` are only there for a finished run.
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
        for key in ("config_sha256", "model", "mode", "temperature"):
            state[key] = made.get(key)
    config = run_dir / "run_config.yaml"
    if config.exists():
        state["run_config_sha256"] = sha256(config)
    return state


def build(inputs: dict, runs: dict, repo_root: Path, **extra: object) -> dict:
    """Assemble the provenance record for one experiment run.

    `inputs` maps a name to an input file, `runs` maps a name to an OncoTrace
    run folder. Anything in `extra` (counts, arguments) is stored as given.
    """
    return {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "clinic_repo": repo_state(repo_root),
        "inputs": {
            name: {"path": str(path), "sha256": sha256(Path(path))}
            for name, path in inputs.items()
        },
        "runs": {name: run_state(Path(path)) for name, path in runs.items()},
        **extra,
    }
