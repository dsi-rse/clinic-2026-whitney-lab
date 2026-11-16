"""Summarize the concurrency probe: one row per level of patients run at once.

For each level it counts the patients answered, the patients that ended in a
server error, the requests OpenRouter refused and OncoTrace resent after a wait
("request refused" lines in the run's log), and the patients OncoTrace had to
restart after the resends ran out ("request failed" lines), and gives the wall
time from the run's own timings.json. No report text is written.

Example, from the clinic repo root:
    PYTHONPATH=src python experiments/openrouter_providers/summarize_concurrency.py \
        --level 10=runs/2026-11-16_openrouter_concurrency_w10 \
        --level 20=runs/2026-11-16_openrouter_concurrency_w20 \
        --not-shared "on CRI until the DSI cluster is back"
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from oncotrace_bench.provenance import build, not_shared_tag
from oncotrace_bench.records import load_run

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
CONFIG = EXPERIMENT_DIR / "configs/wafer_us_annotated66.yaml"
ROSTER = REPO_ROOT / "experiments/endometrial_baseline_full/roster_annotated66.csv"
TASK = REPO_ROOT / "tasks/endo_myometrial_invasion.yaml"


def main() -> None:
    """Read each level's run folder and log, and write the table."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--level",
        action="append",
        required=True,
        metavar="N=FOLDER",
        help="patients run at once, and that run's folder (its log is FOLDER.log)",
    )
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    parser.add_argument(
        "--not-shared",
        metavar="REASON",
        help="the run folders are not on the shared cluster yet: say where they are",
    )
    arguments = parser.parse_args()

    levels = {}
    for item in arguments.level:
        level, folder = item.split("=", 1)
        levels[f"w{level}"] = (int(level), Path(folder))
    acknowledged = {}
    if arguments.not_shared:
        acknowledged = {not_shared_tag(name): arguments.not_shared for name in levels}
    # Before the folder exists, so it is not recorded as uncommitted.
    provenance = build(
        inputs={"config": CONFIG, "roster": ROSTER},
        runs={name: folder for name, (_, folder) in levels.items()},
        repo_root=REPO_ROOT,
        task=TASK,
        acknowledged=acknowledged,
    )
    out = arguments.results_dir / (
        datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_concurrency"
    )
    out.mkdir(parents=True)

    rows = []
    for level, folder in levels.values():
        records = load_run(folder)
        answers = [r.get("answer") or {} for r in records.values()]
        statuses = [
            "server_error" if a.get("reason") == "server_error" else a.get("status")
            for a in answers
        ]
        log = Path(f"{folder}.log").read_text(errors="replace")
        timings = json.loads((folder / "timings.json").read_text())
        rows.append(
            [
                level,
                len(records),
                statuses.count("answered"),
                statuses.count("server_error"),
                log.count("request refused"),
                log.count("request failed"),
                round(timings["extract_seconds"] / 60, 1),
            ]
        )
    with (out / "concurrency.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "patients_at_once",
                "patients",
                "answered",
                "server_errors",
                "requests_refused_and_resent",
                "patient_restarts",
                "wall_minutes",
            ]
        )
        writer.writerows(rows)
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (out / "README.md").write_text(
        "# Concurrency probe\n\n"
        "`concurrency.csv`: one row per level of patients run at once on wafer/us, "
        "made by `experiments/openrouter_providers/summarize_concurrency.py` from the "
        "run folders and logs named in `provenance.json`. Rerunning the script on the "
        "same folders reproduces it exactly.\n"
    )
    print(out)


if __name__ == "__main__":
    main()
