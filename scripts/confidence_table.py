"""Print agreement with the human annotations, grouped by model confidence.

Example:
    python scripts/confidence_table.py \
        --run ~/oncotrace-work/runs/endometrial_glm53_20261012 \
        --task tasks/endo_myometrial_invasion.yaml
"""

import argparse
from pathlib import Path

from oncotrace_bench.traceview_summary import add_traceview_to_path, confidence_table

DEFAULT_ANNOTATIONS = Path(__file__).resolve().parent.parent / "annotations"
DEFAULT_PROJECT = "endo_myometrial_invasion"


def main() -> None:
    """Parse arguments, build the table, and print it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="OncoTrace run folder")
    parser.add_argument("--task", type=Path, required=True, help="task contract YAML")
    parser.add_argument(
        "--annotations", type=Path, default=DEFAULT_ANNOTATIONS, help="annotations root"
    )
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="annotation project")
    parser.add_argument(
        "--oncotrace",
        type=Path,
        default=Path.home() / "oncotrace",
        help="OncoTrace clone that holds viewer/ (TraceView)",
    )
    parser.add_argument("--out-dir", type=Path, help="also write confidence.csv here")
    args = parser.parse_args()

    add_traceview_to_path(args.oncotrace.expanduser())
    table = confidence_table(
        args.run.expanduser(), args.task, args.annotations, args.project
    )
    print(table.to_string(index=False))
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.out_dir / "confidence.csv", index=False)


if __name__ == "__main__":
    main()
