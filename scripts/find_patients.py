"""List patients to open in TraceView, filtered by what happened to them.

Examples:
    # which refusals happened, and how many patients did each affect
    python scripts/find_patients.py --run RUN --task TASK --summary
    # unanswered patients stopped by the call budget
    python scripts/find_patients.py --run RUN --task TASK --no-answer \
        --reason model_call_budget_exhausted
    # patients (answered or not) with a reply cut off at the token cap
    python scripts/find_patients.py --run RUN --task TASK --cut-off
"""

import argparse
from pathlib import Path

from oncotrace_bench.traceview_summary import (
    add_traceview_to_path,
    find_units,
    load_views,
    refusal_summary,
)


def main() -> None:
    """Parse arguments, apply the filters, and print the matching patients."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="OncoTrace run folder")
    parser.add_argument("--task", type=Path, required=True, help="task contract YAML")
    parser.add_argument(
        "--summary", action="store_true", help="group refusals by signature instead"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--answered", action="store_true", help="accepted answers only")
    group.add_argument("--no-answer", action="store_true", help="unanswered only")
    parser.add_argument("--reason", help="one recorded stop reason")
    parser.add_argument("--refused-with", help="refusal signature seen at least once")
    parser.add_argument(
        "--cut-off", action="store_true", help="a reply hit the token cap"
    )
    parser.add_argument("--out", type=Path, help="also write the table as CSV")
    parser.add_argument(
        "--oncotrace",
        type=Path,
        default=Path.home() / "oncotrace",
        help="OncoTrace clone that holds viewer/ (TraceView)",
    )
    args = parser.parse_args()

    add_traceview_to_path(args.oncotrace.expanduser())
    views = load_views(args.run.expanduser(), args.task)

    if args.summary:
        table = refusal_summary(views)
    else:
        answered = True if args.answered else False if args.no_answer else None
        table = find_units(
            views, answered, args.reason, args.refused_with, args.cut_off
        )
    print(table.to_string(index=False))
    if args.out:
        table.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
