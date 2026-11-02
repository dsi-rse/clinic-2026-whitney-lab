"""Tests for the provenance helper.

These use temporary folders and hand-written records, so a reviewer can run them
without cluster access or membership of the `__oncotrace` group.
"""

import json
from pathlib import Path

from oncotrace_bench.provenance import build, check, model_root, server_starts

CLEAN_RECORD = {
    "clinic_repo": {"commit": "a" * 40, "uncommitted_files": []},
    "runs": {
        "t0": {
            "path": "",
            "oncotrace_commits": ["b" * 40],
            "contract_digests": ["c" * 64],
            "oncotrace_modified": False,
            "group_readable": True,
            "server_starts": [{"job_id": "1", "logs": [], "failed": False}],
        }
    },
}


def record_with(**run_fields: object) -> dict:
    """A clean record whose one run has these fields replaced."""
    record = json.loads(json.dumps(CLEAN_RECORD))
    record["runs"]["t0"].update(run_fields)
    return record


def test_clean_record_has_no_problems(tmp_path: Path) -> None:
    """A record naming one commit, one digest and a readable run passes."""
    record = record_with(path=str(tmp_path))
    assert check(record) == []


def test_dirty_checkout_is_a_problem(tmp_path: Path) -> None:
    """A result made from an uncommitted tree is reported, one file at a time."""
    record = record_with(path=str(tmp_path))
    record["clinic_repo"]["uncommitted_files"] = ["experiments/"]
    problems = check(record)
    assert len(problems) == 1
    assert "experiments/" in problems[0]


def test_record_without_runs_is_a_problem() -> None:
    """A record that names no run cannot say what produced the answers."""
    problems = check({"clinic_repo": {"commit": "a" * 40, "uncommitted_files": []}})
    assert any("no runs recorded" in problem for problem in problems)


def test_two_commits_in_one_run_is_a_problem(tmp_path: Path) -> None:
    """A run split across OncoTrace versions is not one experiment."""
    record = record_with(path=str(tmp_path), oncotrace_commits=["b" * 40, "d" * 40])
    assert any("2 OncoTrace commits" in problem for problem in check(record))


def test_missing_run_folder_is_a_problem() -> None:
    """A record pointing at a run that is gone cannot be checked by anyone."""
    record = record_with(path="/does/not/exist")
    assert any("is gone" in problem for problem in check(record))


def test_server_starts_finds_the_failed_allocation(tmp_path: Path) -> None:
    """Both allocations are found, and the failed one is marked.

    A run's own provenance names only the last job, so a first server that died
    would otherwise be invisible.
    """
    for name in ("job-11.out", "server-11-failed.log", "job-22.out", "server.log"):
        (tmp_path / name).touch()
    starts = server_starts(tmp_path)
    assert [start["job_id"] for start in starts] == ["11", "22"]
    assert [start["failed"] for start in starts] == [True, False]


def test_two_server_starts_is_a_problem(tmp_path: Path) -> None:
    """Repeats that span two server starts may not mean what a reader assumes."""
    record = record_with(
        path=str(tmp_path),
        server_starts=[
            {"job_id": "11", "logs": [], "failed": True},
            {"job_id": "22", "logs": [], "failed": False},
        ],
    )
    assert any("spans 2 server starts" in problem for problem in check(record))


def test_model_root_comes_from_the_serving_block(tmp_path: Path) -> None:
    """The checkpoint path is read from `serving.model_root`, or is empty."""
    config = tmp_path / "run_config.yaml"
    config.write_text("serving:\n  model_root: /weights/GLM-5.3-Flash-stripe8\n")
    assert model_root(config) == "/weights/GLM-5.3-Flash-stripe8"
    config.write_text("mode: agentic\n")
    assert model_root(config) == ""


def test_build_hashes_inputs_and_the_task(tmp_path: Path) -> None:
    """Inputs and the task contract are hashed; extras are stored as given."""
    roster = tmp_path / "roster.csv"
    roster.write_text("unit\nTCGA-A5-A0GJ\n")
    task = tmp_path / "task.yaml"
    task.write_text("name: endo_myometrial_invasion\n")
    record = build(
        inputs={"roster": roster},
        runs={},
        repo_root=tmp_path,
        task=task,
        command="pytest",
    )
    assert len(record["inputs"]["roster"]["sha256"]) == 64  # noqa: PLR2004
    assert len(record["task_sha256"]) == 64  # noqa: PLR2004
    assert record["command"] == "pytest"


def test_build_separates_the_analysis_checkout(tmp_path: Path) -> None:
    """A checkout the analysis imports from is recorded apart from the runs."""
    record = build(
        inputs={}, runs={}, repo_root=tmp_path, analysis_repos={"oncotrace": tmp_path}
    )
    assert "oncotrace" in record["analysis_repos"]
    assert "runs" in record
