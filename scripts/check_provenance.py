"""Check the provenance records under a folder before opening a PR.

Runs the checks in `oncotrace_bench.provenance.check` on every
`provenance.json` it finds, and additionally asks GitHub whether each recorded
commit was pushed. A commit that exists on GitHub but was recorded from a dirty
checkout is still a problem, so both are checked.

Usage:
    PYTHONPATH=src python scripts/check_provenance.py [paths ...] [--no-github]

With no paths, it checks `experiments/`. Exits non-zero if anything is wrong.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from oncotrace_bench.provenance import check

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATHS = [REPO_ROOT / "experiments"]


def records(paths: list[Path]) -> list[Path]:
    """Every provenance.json at or under the given files and folders."""
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(path.rglob("provenance.json")))
        elif path.is_file():
            found.append(path)
    return found


def remote_slug(repo: Path) -> str:
    """The 'owner/name' of a checkout's origin remote, or '' if there is none."""
    git = shutil.which("git")
    if git is None:
        return ""
    done = subprocess.run(  # noqa: S603 - fixed read-only git arguments, no user input
        [git, "-C", str(repo), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    url = done.stdout.strip().removesuffix(".git")
    if not url:
        return ""
    return "/".join(url.replace(":", "/").split("/")[-2:])


def pushed(slug: str, commit: str) -> bool:
    """Whether GitHub has this commit. True if we cannot ask, so we don't cry wolf."""
    gh = shutil.which("gh")
    if gh is None or not slug or not commit:
        return True
    done = subprocess.run(  # noqa: S603 - arguments built from a git remote and a sha
        [gh, "api", f"repos/{slug}/commits/{commit}", "--jq", ".sha"],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def commit_problems(record: dict, slug: str) -> list[str]:
    """Recorded commits that were never pushed, so nobody else can check them out."""
    problems = []
    repos = {"clinic_repo": record.get("clinic_repo") or {}}
    repos.update(record.get("analysis_repos") or {})
    for name, repo in repos.items():
        commit = repo.get("commit") or ""
        if commit and not pushed(slug, commit):
            problems.append(f"{name}.commit {commit[:8]} is not on GitHub")
    return problems


def main() -> None:
    """Check every provenance record found, print the problems, and set the status."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=DEFAULT_PATHS,
        help="provenance.json files, or folders to search (default: experiments/)",
    )
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="skip asking GitHub whether the recorded commits were pushed",
    )
    arguments = parser.parse_args()

    slug = "" if arguments.no_github else remote_slug(REPO_ROOT)
    found = records(list(arguments.paths))
    if not found:
        print("no provenance.json found")
        return

    total = 0
    for path in found:
        record = json.loads(path.read_text())
        problems = check(record) + commit_problems(record, slug)
        shown = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
        if problems:
            total += len(problems)
            print(f"{shown}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"{shown}: ok")

    print(f"\n{len(found)} record(s) checked, {total} problem(s)")
    if total:
        sys.exit(1)


if __name__ == "__main__":
    main()
