"""Print a text-free summary of what OncoTrace did for chosen patients.

Example:
    python scripts/inspect_patients.py \
        --run ~/oncotrace-work/runs/endometrial_glm53_20261012 \
        --task tasks/endo_myometrial_invasion.yaml \
        --units TCGA-A5-A0GP TCGA-A5-A0GE
"""

import argparse
from pathlib import Path

from oncotrace_bench.traceview_summary import add_traceview_to_path, trajectory_facts

STEP_KEY = "I=inventory R=read S=search $=submit !=refused ?=other x=no answer"


def main() -> None:
    """Parse arguments and print one block of facts per patient."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="OncoTrace run folder")
    parser.add_argument("--task", type=Path, required=True, help="task contract YAML")
    parser.add_argument("--units", nargs="+", required=True, help="patient IDs")
    parser.add_argument(
        "--oncotrace",
        type=Path,
        default=Path.home() / "oncotrace",
        help="OncoTrace clone that holds viewer/ (TraceView)",
    )
    args = parser.parse_args()

    add_traceview_to_path(args.oncotrace.expanduser())
    import records as traceview

    tasks, _, _ = traceview.load_tasks([args.task])
    views = {v.unit: v for v in traceview.load_run(args.run.expanduser(), tasks)}

    print(f"step key: {STEP_KEY}")
    for unit in args.units:
        print()
        if unit not in views:
            print(f"{unit}: no record in this run")
            continue
        for name, value in trajectory_facts(views[unit]).items():
            print(f"{name}: {value}")


if __name__ == "__main__":
    main()
