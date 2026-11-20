"""Build the two revising agents' workspaces for the contract-guidelines test.

Picks the example reports the agents may read: patients from the full roster
who are NOT among the 66 annotated patients the contracts are scored on, chosen
at random with a fixed seed. Writes their IDs to a committed CSV, and copies the
reports, the old contract, OncoTrace's contract reference and (for the guided
arm only) the guidelines into one folder per arm. The workspaces hold report
text, so put them outside Git.

Example:
    python experiments/contract_guidelines/make_workspaces.py \
        --oncotrace ../oncotrace --out /path/outside/git
"""

import argparse
import csv
import json
import random
import shutil
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
FULL_ROSTER = REPO_ROOT / "data" / "endometrial" / "roster_ucec.csv"
SCORED_ROSTER = (
    REPO_ROOT / "experiments" / "endometrial_baseline_full" / "roster_annotated66.csv"
)
REPORTS = (
    REPO_ROOT / "data" / "endometrial" / "documents" / "ucec_pathology_report.jsonl"
)
OLD_CONTRACT = REPO_ROOT / "tasks" / "endo_myometrial_invasion.yaml"
GUIDELINES = REPO_ROOT / "docs" / "task-contract-guidelines.md"
SAMPLE_CSV = EXPERIMENT_DIR / "inputs" / "example_reports.csv"


def read_units(path: Path) -> list[str]:
    """Return the `unit` column of a roster CSV."""
    with path.open(newline="") as handle:
        return [row["unit"] for row in csv.DictReader(handle)]


def main() -> None:
    """Choose the example reports and write both workspaces."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--oncotrace", type=Path, required=True, help="OncoTrace clone")
    parser.add_argument("--out", type=Path, required=True, help="folder outside Git")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=44)
    args = parser.parse_args()

    scored = set(read_units(SCORED_ROSTER))
    candidates = sorted(set(read_units(FULL_ROSTER)) - scored)
    chosen = sorted(random.Random(args.seed).sample(candidates, args.count))  # noqa: S311 (not security)
    with SAMPLE_CSV.open("w", newline="") as handle:
        csv.writer(handle).writerows([["unit"], *[[unit] for unit in chosen]])

    texts = {}
    with REPORTS.open() as handle:
        for line in handle:
            record = json.loads(line)
            unit = record["unit"]
            if unit in chosen:
                texts[unit] = record["text"]
    missing = set(chosen) - set(texts)
    if missing:
        raise SystemExit(f"no report for {len(missing)} chosen patients")

    for arm in ("unguided", "guided"):
        folder = args.out / arm
        (folder / "reports").mkdir(parents=True, exist_ok=False)
        shutil.copy(OLD_CONTRACT, folder / "contract.yaml")
        shutil.copy(
            args.oncotrace / "docs" / "task-contract.md", folder / "task-contract.md"
        )
        if arm == "guided":
            shutil.copy(GUIDELINES, folder / "guidelines.md")
        for unit, text in texts.items():
            (folder / "reports" / f"{unit}.txt").write_text(text)
    print(
        f"{len(chosen)} example reports, none of them scored; workspaces in {args.out}"
    )


if __name__ == "__main__":
    main()
