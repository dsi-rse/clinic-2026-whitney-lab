"""Print how many patients were accepted, unanswered, server errors, or unfinished.

Example:
    python scripts/outcome_table.py \
        --run ~/oncotrace-work/runs/endometrial_glm53_20261012 \
        --task tasks/endo_myometrial_invasion.yaml \
        --roster /net/spaces/annawoodard/oncotrace/data/endometrial/roster_ucec.csv
"""

import argparse
from pathlib import Path

from oncotrace_bench.traceview_summary import (
    add_traceview_to_path,
    outcome_table,
    read_roster,
)


def main() -> None:
    """Parse arguments, build the tables, and print (and optionally save) them."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="OncoTrace run folder")
    parser.add_argument("--task", type=Path, required=True, help="task contract YAML")
    parser.add_argument("--roster", type=Path, required=True, help="roster CSV")
    parser.add_argument(
        "--oncotrace",
        type=Path,
        default=Path.home() / "oncotrace",
        help="OncoTrace clone that holds viewer/ (TraceView)",
    )
    parser.add_argument("--out-dir", type=Path, help="also write one CSV per table")
    args = parser.parse_args()

    add_traceview_to_path(args.oncotrace.expanduser())
    tables = outcome_table(
        args.run.expanduser(), args.task, read_roster(args.roster)
    )

    for name, table in tables.items():
        print(f"\n{name}")
        print(table.to_string(index=False))
        if args.out_dir:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            table.to_csv(args.out_dir / f"{name}.csv", index=False)


if __name__ == "__main__":
    main()
