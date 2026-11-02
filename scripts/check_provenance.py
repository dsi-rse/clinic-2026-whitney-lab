"""Check the provenance records you are about to open a PR with.

Runs the checks in `oncotrace_bench.provenance.check` on each `provenance.json`,
and additionally asks GitHub whether each recorded commit was pushed. A commit
that exists on GitHub but was recorded from a dirty checkout is still a problem,
so both are checked.

With no paths, it checks only the records added or changed against
`origin/main`, which is your own work. To audit everything already committed,
name a folder: `make check-provenance ARGS=experiments`. Older records that
predate the shared helper are expected to fail that audit; see issue #31.

Usage:
    PYTHONPATH=src python scripts/check_provenance.py [paths ...] [--no-github]

Exits non-zero if anything is wrong.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from oncotrace_bench.provenance import check, remote_slug

REPO_ROOT = Path(__file__).resolve().parent.parent

# The OncoTrace repository the runs' commits belong to. A run's OncoTrace commit
# is never in the clinic repo, so it has to be asked about separately.
ONCOTRACE_REPO = "dsi-rse/oncotrace"

UNKNOWN = "unknown"


def _git(*args: str) -> tuple[bool, str]:
    """Run one read-only git command in this checkout."""
    git = shutil.which("git")
    if git is None:
        return False, ""
    done = subprocess.run(  # noqa: S603 - fixed read-only git arguments, no user input
        [git, "-C", str(REPO_ROOT), *args], capture_output=True, text=True, check=False
    )
    return done.returncode == 0, done.stdout.strip()


def changed_records() -> list[Path]:
    """The provenance records added or changed against `origin/main`."""
    names: list[str] = []
    for args in (
        ("diff", "--name-only", "origin/main", "--"),
        ("ls-files", "--others", "--exclude-standard", "--"),
    ):
        ok, out = _git(*args, "*/provenance.json")
        if ok:
            names.extend(out.splitlines())
    paths = {REPO_ROOT / name for name in names if name}
    return sorted(path for path in paths if path.is_file())


def records(paths: list[Path]) -> list[Path]:
    """Every provenance.json at or under the given files and folders."""
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(path.rglob("provenance.json")))
        elif path.is_file():
            found.append(path)
    return found


def clinic_slug() -> str:
    """The 'owner/name' of this checkout's origin remote, or ''."""
    ok, url = _git("remote", "get-url", "origin")
    return remote_slug(url) if ok else ""


def pushed(slug: str, commit: str) -> str:
    """Whether GitHub has this commit: "yes", "no", or "unknown".

    "unknown" matters: a missing `gh`, a login that has expired, or no network
    must not read as either a pass or a failure.
    """
    gh = shutil.which("gh")
    if gh is None:
        return UNKNOWN
    if not slug or not commit:
        return UNKNOWN
    done = subprocess.run(  # noqa: S603 - arguments built from a git remote and a sha
        [gh, "api", f"repos/{slug}/commits/{commit}", "--jq", ".sha"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode == 0:
        return "yes"
    # A 422/404 means GitHub answered and does not have it; anything else
    # (auth, network, rate limit) means we could not ask.
    answered = "No commit found" in done.stderr or "Not Found" in done.stderr
    return "no" if answered else UNKNOWN


def recorded_commits(record: dict, fallback: str) -> list[tuple[str, str, str]]:
    """Every commit in a record, as (what it is, its repository slug, the sha).

    Each checkout is asked about in its own repository: an OncoTrace commit is
    looked up in the OncoTrace repo, not in the clinic repo. `fallback` is used
    for an older record whose `clinic_repo` has no `remote` field.
    """
    wanted = []
    clinic = record.get("clinic_repo") or {}
    if clinic.get("commit"):
        wanted.append(
            ("clinic_repo", clinic.get("remote") or fallback, clinic["commit"])
        )
    for name, repo in (record.get("analysis_repos") or {}).items():
        if repo.get("commit"):
            wanted.append(
                (f"analysis repo {name}", repo.get("remote", ""), repo["commit"])
            )
    for name, run in (record.get("runs") or {}).items():
        for commit in run.get("oncotrace_commits") or []:
            wanted.append((f"run {name} OncoTrace", ONCOTRACE_REPO, commit))
    return wanted


def commit_problems(record: dict, fallback: str) -> tuple[list[str], list[str]]:
    """Recorded commits GitHub does not have, and the ones we could not ask about."""
    problems, unknowns = [], []
    for what, slug, commit in recorded_commits(record, fallback):
        answer = pushed(slug, commit)
        if answer == "no":
            problems.append(
                f"{what} commit {commit[:8]} is not on GitHub"
                f"{f' ({slug})' if slug else ''}, so nobody else can check it out"
            )
        elif answer == UNKNOWN:
            where = slug or "no remote recorded"
            unknowns.append(f"{what} commit {commit[:8]} not checked ({where})")
    return problems, unknowns


def notes(record: dict) -> list[str]:
    """What the record cannot speak to, and the exceptions it acknowledges.

    These are printed but never counted as problems: an acknowledged exception
    is allowed by `AGENTS.md`, and an unknown is not evidence of a fault.
    """
    lines = [
        f"acknowledged {tag}: {reason}"
        for tag, reason in (record.get("acknowledged") or {}).items()
    ]
    lines += [
        f"run {name}: no job log in the run folder, so how many server starts "
        "served it is unknown, not one"
        for name, run in (record.get("runs") or {}).items()
        if run.get("server_starts_known") is False
    ]
    return lines


def main() -> None:
    """Check each provenance record found, print the problems, and set the status."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="provenance.json files, or folders to search. Default: the records "
        "added or changed against origin/main.",
    )
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="skip asking GitHub whether the recorded commits were pushed",
    )
    arguments = parser.parse_args()

    found = records(list(arguments.paths)) if arguments.paths else changed_records()
    if not found:
        print("no new or changed provenance.json; nothing to check")
        return

    fallback = "" if arguments.no_github else clinic_slug()
    total = 0
    for path in found:
        record = json.loads(path.read_text())
        problems = check(record)
        unknowns: list[str] = []
        if not arguments.no_github:
            extra, unknowns = commit_problems(record, fallback)
            problems += extra
        shown = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
        total += len(problems)
        print(f"{shown}{'' if problems else ': ok'}")
        for problem in problems:
            print(f"  - {problem}")
        for unknown in unknowns + notes(record):
            print(f"  ? {unknown}")

    print(f"\n{len(found)} record(s) checked, {total} problem(s)")
    if total:
        sys.exit(1)


if __name__ == "__main__":
    main()
