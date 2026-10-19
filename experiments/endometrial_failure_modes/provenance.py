"""Record what a result folder was made from, so it can be remade later."""

import hashlib
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
    """The SHA-256 of a file, to show which version of a contract was used."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(inputs: dict, counts: dict, repo_root: Path, oncotrace: Path) -> dict:
    """Assemble the provenance record for one experiment run.

    `inputs` holds the paths used, `counts` the sizes of what was read.
    """
    return {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "inputs": {key: str(value) for key, value in inputs.items()},
        "task_sha256": sha256(Path(inputs["task"])),
        "counts": counts,
        "oncotrace": repo_state(oncotrace),
        "clinic_repo": repo_state(repo_root),
    }
