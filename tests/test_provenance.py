"""Tests for the provenance helper and the check script.

These use temporary folders, `git init` repos and hand-written records, so they
run without cluster access, without the `__oncotrace` group, and without the
network. Nothing here reads a real run folder.
"""

import importlib.util
import json
import os
import stat
import subprocess
from pathlib import Path

from oncotrace_bench.provenance import (
    build,
    check,
    group_access,
    model_root,
    remote_slug,
    repo_state,
    run_state,
    server_starts,
)

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_provenance.py"

# SHA-256 of the single byte "x", so a wrong file or wrong encoding fails.
SHA256_OF_X = "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"

COMMIT = "b" * 40
DIGEST = "c" * 64

CLEAN_RECORD = {
    "clinic_repo": {"commit": "a" * 40, "remote": "o/r", "uncommitted_files": []},
    "runs": {
        "t0": {
            "path": "",
            "records": 2,
            "units_without_contract": 0,
            "oncotrace_commits": [COMMIT],
            "contract_digests": [DIGEST],
            "oncotrace_modified": False,
            "group_access": {"reachable": True, "chain": []},
            "server_starts": [
                {"job_id": "1", "log": "job-1.out", "published_endpoint": True}
            ],
        }
    },
}


def check_script() -> object:
    """Import `scripts/check_provenance.py`, which is not a package module."""
    spec = importlib.util.spec_from_file_location("check_provenance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record_with(**run_fields: object) -> dict:
    """A clean record whose one run has these fields replaced."""
    record = json.loads(json.dumps(CLEAN_RECORD))
    record["runs"]["t0"].update(run_fields)
    return record


def git_repo(path: Path, remote: str | None = None) -> Path:
    """A real git repo with one commit, so `repo_state` can be tested for real."""
    path.mkdir(parents=True, exist_ok=True)
    run = ["git", "-C", str(path)]
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    subprocess.run([*run, "init", "-q", "-b", "main"], check=True, env=env)  # noqa: S603, S607
    subprocess.run([*run, "config", "user.email", "t@t"], check=True, env=env)  # noqa: S603, S607
    subprocess.run([*run, "config", "user.name", "t"], check=True, env=env)  # noqa: S603, S607
    (path / "kept.txt").write_text("kept\n")
    subprocess.run([*run, "add", "kept.txt"], check=True, env=env)  # noqa: S603, S607
    subprocess.run([*run, "commit", "-q", "-m", "first"], check=True, env=env)  # noqa: S603, S607
    if remote:
        subprocess.run([*run, "remote", "add", "origin", remote], check=True, env=env)  # noqa: S603, S607
    return path


def fake_run(path: Path, units: list[dict], **files: dict) -> Path:
    """A run folder shaped like OncoTrace's, with the unit records given."""
    (path / "units").mkdir(parents=True)
    for index, unit in enumerate(units):
        (path / "units" / f"TCGA-{index}.json").write_text(json.dumps(unit))
    for name, body in files.items():
        (path / f"{name}.json").write_text(json.dumps(body))
    return path


# --- check(): the cases a reviewer would otherwise check by hand ---------------


def test_clean_record_has_no_problems(tmp_path: Path) -> None:
    """A record naming one commit, one digest and a reachable run passes."""
    assert check(record_with(path=str(tmp_path))) == []


def test_dirty_checkout_is_a_problem(tmp_path: Path) -> None:
    """A result made from an uncommitted tree is reported, one file at a time."""
    record = record_with(path=str(tmp_path))
    record["clinic_repo"]["uncommitted_files"] = ["experiments/"]
    problems = check(record)
    assert len(problems) == 1
    assert "experiments/" in problems[0]


def test_an_explained_dirty_checkout_passes(tmp_path: Path) -> None:
    """`dirty_reason` is how AGENTS.md's "or explain why not" reaches the tool."""
    record = record_with(path=str(tmp_path))
    record["clinic_repo"]["uncommitted_files"] = ["experiments/"]
    record["dirty_reason"] = "the report store cannot be committed"
    assert check(record) == []


def test_git_failure_is_a_problem_not_a_clean_record(tmp_path: Path) -> None:
    """A checkout git could not read must not read as clean at no commit."""
    record = record_with(path=str(tmp_path))
    record["clinic_repo"] = {"commit": "", "uncommitted_files": [], "error": "refused"}
    assert any("git could not be read" in problem for problem in check(record))


def test_record_without_runs_is_a_problem() -> None:
    """A record that names no run cannot be checked as a run."""
    problems = check({"clinic_repo": {"commit": "a" * 40, "uncommitted_files": []}})
    assert any("no runs recorded" in problem for problem in problems)


def test_two_commits_in_one_run_is_a_problem(tmp_path: Path) -> None:
    """A run split across OncoTrace versions is not one experiment."""
    record = record_with(path=str(tmp_path), oncotrace_commits=[COMMIT, "d" * 40])
    assert any("2 OncoTrace commits" in problem for problem in check(record))


def test_units_without_a_contract_are_reported(tmp_path: Path) -> None:
    """Units with no contract must not be quietly dropped from the counts."""
    record = record_with(path=str(tmp_path), units_without_contract=1)
    assert any("1 unit record(s) with no contract" in p for p in check(record))


def test_missing_run_path_is_a_problem() -> None:
    """A run entry with no path must not pass, as `Path("")` would."""
    record = record_with()
    del record["runs"]["t0"]["path"]
    assert any("records no path" in problem for problem in check(record))


def test_missing_run_folder_is_a_problem() -> None:
    """A record pointing at a run that is gone cannot be checked by anyone."""
    assert any("is gone" in problem for problem in check(record_with(path="/no/such")))


def test_unreachable_run_folder_is_reported_not_raised(tmp_path: Path) -> None:
    """An unreadable parent folder must be reported, not crash the whole run.

    `Path.exists()` raises PermissionError here on Python 3.12.
    """
    outer = tmp_path / "outer"
    (outer / "run").mkdir(parents=True)
    outer.chmod(0o000)
    try:
        problems = check(record_with(path=str(outer / "run")))
    finally:
        outer.chmod(0o755)
    assert len(problems) == 1
    assert "cannot be reached" in problems[0] or "is gone" in problems[0]


def test_a_run_the_group_cannot_reach_is_a_problem(tmp_path: Path) -> None:
    """A private folder above the run makes it unreachable, whatever its own mode."""
    record = record_with(
        path=str(tmp_path),
        group_access={
            "reachable": False,
            "chain": [
                {"path": "/net", "group": "root", "group_ok": True},
                {"path": "/net/private", "group": "someone", "group_ok": False},
            ],
        },
    )
    assert any("/net/private" in problem for problem in check(record))


# --- server starts: the failed-start false alarm the review found -------------


def test_a_failed_start_is_not_a_problem(tmp_path: Path) -> None:
    """A server that died before publishing an endpoint served no units.

    The run was not resumed or split, so this must not be flagged.
    """
    record = record_with(
        path=str(tmp_path),
        server_starts=[
            {"job_id": "11", "log": "job-11.out", "published_endpoint": False},
            {"job_id": "22", "log": "job-22.out", "published_endpoint": True},
        ],
    )
    assert check(record) == []


def test_two_serving_starts_is_a_problem(tmp_path: Path) -> None:
    """Two allocations that both served means the repeats may not be comparable."""
    record = record_with(
        path=str(tmp_path),
        server_starts=[
            {"job_id": "11", "log": "job-11.out", "published_endpoint": True},
            {"job_id": "22", "log": "job-22.out", "published_endpoint": True},
        ],
    )
    assert any("served by 2 server starts" in problem for problem in check(record))


def test_server_starts_reads_the_endpoint_marker(tmp_path: Path) -> None:
    """Whether a start served is read from its log, not from the file name."""
    (tmp_path / "job-11.out").write_text(
        "server exited before publishing an endpoint\n"
    )
    (tmp_path / "job-22.out").write_text("endpoint ready at http://127.0.0.1:1/v1\n")
    (tmp_path / "server.log").touch()
    starts = server_starts(tmp_path)
    assert [start["job_id"] for start in starts] == ["11", "22"]
    assert [start["published_endpoint"] for start in starts] == [False, True]


def test_a_cancelled_start_with_no_endpoint_line_did_not_serve(tmp_path: Path) -> None:
    """The October 13 runs have no `-failed` file name, only a CANCELLED line."""
    (tmp_path / "job-11.out").write_text("CANCELLED AT 2026-10-13T19:19:48\n")
    assert server_starts(tmp_path)[0]["published_endpoint"] is False


# --- disagreement between the unit records and the run's own provenance -------


def test_a_run_provenance_that_contradicts_its_units_is_a_problem(
    tmp_path: Path,
) -> None:
    """The run record and the unit records must name the same OncoTrace commit."""
    record = record_with(path=str(tmp_path), raw={"commit": "e" * 40})
    assert any("but its unit records say" in problem for problem in check(record))


def test_a_unit_count_that_disagrees_is_a_problem(tmp_path: Path) -> None:
    """A run that says 50 units but holds 2 records was read incompletely."""
    record = record_with(path=str(tmp_path), raw={"unit_count": 50})
    assert any("but its provenance says 50 units" in p for p in check(record))


# --- repo_state, run_state, group_access, model_root -------------------------


def test_repo_state_reads_a_real_checkout(tmp_path: Path) -> None:
    """A clean repo records its commit, branch and remote slug, and no error."""
    repo = git_repo(tmp_path / "repo", remote="git@github.com:owner/name.git")
    state = repo_state(repo)
    assert len(state["commit"]) == 40  # noqa: PLR2004
    assert state["branch"] == "main"
    assert state["remote"] == "owner/name"
    assert state["uncommitted_files"] == []
    assert "error" not in state


def test_repo_state_sees_an_uncommitted_file(tmp_path: Path) -> None:
    """An untracked file is reported, since it is not in the recorded commit."""
    repo = git_repo(tmp_path / "repo")
    (repo / "scratch.txt").write_text("not committed\n")
    assert repo_state(repo)["uncommitted_files"] == ["scratch.txt"]


def test_repo_state_records_an_error_for_a_path_that_is_not_a_repo(
    tmp_path: Path,
) -> None:
    """A typo'd or un-cloned path must not record as a clean checkout."""
    state = repo_state(tmp_path / "not-a-repo")
    assert state["commit"] == ""
    assert state["error"]


def test_run_state_reads_a_run_folder(tmp_path: Path) -> None:
    """Unit facts and the run's own provenance are both kept, and `raw` with them."""
    contract = {"commit": COMMIT, "digest": DIGEST, "package_modified": False}
    fake_run(
        tmp_path / "run",
        [{"contract": contract}, {"contract": contract}],
        provenance={"unit_count": 2, "model": "glm", "timings": {"job_id": "7"}},
        endpoint={"job_id": "7", "node": "o001"},
    )
    state = run_state(tmp_path / "run")
    assert state["records"] == 2  # noqa: PLR2004
    assert state["oncotrace_commits"] == [COMMIT]
    assert state["contract_digests"] == [DIGEST]
    assert state["units_without_contract"] == 0
    assert state["job_id"] == "7"
    assert state["model"] == "glm"
    assert state["raw"]["unit_count"] == 2  # noqa: PLR2004
    assert state["endpoint"]["node"] == "o001"


def test_run_state_counts_units_with_no_contract(tmp_path: Path) -> None:
    """A partial run where some units carry no contract must say so."""
    contract = {"commit": COMMIT, "digest": DIGEST}
    fake_run(tmp_path / "run", [{"contract": contract}, {}])
    state = run_state(tmp_path / "run")
    assert state["records"] == 2  # noqa: PLR2004
    assert state["units_without_contract"] == 1
    assert state["contract_digests"] == [DIGEST]


def test_group_access_follows_the_whole_path(tmp_path: Path) -> None:
    """A group-readable folder under a private one is still unreachable."""
    outer = tmp_path / "outer"
    run = outer / "run"
    run.mkdir(parents=True)
    run.chmod(0o750)
    outer.chmod(stat.S_IRWXU)
    try:
        access = group_access(run)
    finally:
        outer.chmod(0o755)
    assert access["reachable"] is False


def test_model_root_comes_from_the_serving_block(tmp_path: Path) -> None:
    """The checkpoint path is read from `serving.model_root`, or is empty."""
    config = tmp_path / "run_config.yaml"
    config.write_text("serving:\n  model_root: /weights/GLM-5.3-Flash-stripe8\n")
    assert model_root(config) == "/weights/GLM-5.3-Flash-stripe8"
    config.write_text("mode: agentic\n")
    assert model_root(config) == ""


def test_remote_slug_handles_both_url_shapes() -> None:
    """Both remote URL shapes reduce to owner/name; nothing else does."""
    assert remote_slug("git@github.com:dsi-rse/oncotrace.git") == "dsi-rse/oncotrace"
    assert remote_slug("https://github.com/dsi-rse/oncotrace") == "dsi-rse/oncotrace"
    assert remote_slug("") == ""


# --- build() ------------------------------------------------------------------


def test_build_hashes_inputs_and_the_task(tmp_path: Path) -> None:
    """Inputs and the task contract are hashed, and extras stored as given."""
    roster = tmp_path / "roster.csv"
    roster.write_bytes(b"x")
    task = tmp_path / "task.yaml"
    task.write_bytes(b"x")
    record = build(
        inputs={"roster": roster},
        runs={},
        repo_root=tmp_path,
        task=task,
        command="pytest",
    )
    assert record["inputs"]["roster"]["sha256"] == SHA256_OF_X
    assert record["task_sha256"] == SHA256_OF_X
    assert record["command"] == "pytest"


def test_build_records_the_analysis_checkout_with_its_commit(tmp_path: Path) -> None:
    """A checkout the analysis imports from is recorded apart from the runs."""
    repo = git_repo(
        tmp_path / "oncotrace", remote="git@github.com:dsi-rse/oncotrace.git"
    )
    record = build(
        inputs={}, runs={}, repo_root=repo, analysis_repos={"oncotrace": repo}
    )
    entry = record["analysis_repos"]["oncotrace"]
    assert len(entry["commit"]) == 40  # noqa: PLR2004
    assert entry["remote"] == "dsi-rse/oncotrace"
    assert "runs" in record


def test_an_analysis_repo_that_recorded_nothing_is_a_problem(tmp_path: Path) -> None:
    """A typo'd analysis-repo path records no commit, and must not pass."""
    record = build(
        inputs={},
        runs={},
        repo_root=git_repo(tmp_path / "repo"),
        analysis_repos={"oncotrace": tmp_path / "missing"},
    )
    assert any("analysis repo oncotrace" in problem for problem in check(record))


# --- the check script ---------------------------------------------------------


def test_each_commit_is_looked_up_in_its_own_repository() -> None:
    """An OncoTrace commit must not be looked for in the clinic repo.

    This is the whole point: a run's OncoTrace commit and an analysis checkout's
    commit live in a different repository from the clinic commit.
    """
    module = check_script()
    record = {
        "clinic_repo": {
            "commit": "a" * 40,
            "remote": "dsi-rse/clinic",
            "uncommitted_files": [],
        },
        "analysis_repos": {
            "oncotrace": {"commit": "f" * 40, "remote": "dsi-rse/oncotrace"}
        },
        "runs": {"t0": {"oncotrace_commits": [COMMIT]}},
    }
    wanted = module.recorded_commits(record, fallback="fallback/slug")
    assert ("clinic_repo", "dsi-rse/clinic", "a" * 40) in wanted
    assert ("analysis repo oncotrace", "dsi-rse/oncotrace", "f" * 40) in wanted
    assert ("run t0 OncoTrace", module.ONCOTRACE_REPO, COMMIT) in wanted


def test_an_older_record_falls_back_to_this_checkouts_remote() -> None:
    """A record written before `remote` existed still gets its clinic commit checked."""
    module = check_script()
    record = {"clinic_repo": {"commit": "a" * 40}, "runs": {}}
    assert module.recorded_commits(record, fallback="o/r")[0][1] == "o/r"


def test_an_unaskable_commit_is_unknown_not_a_failure() -> None:
    """With no slug there is no question to ask, so it must not read as "not pushed"."""
    module = check_script()
    assert module.pushed("", "a" * 40) == module.UNKNOWN
    assert module.pushed("o/r", "") == module.UNKNOWN
