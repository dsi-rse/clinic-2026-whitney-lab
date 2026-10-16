"""Make edited report copies for an evidence-following experiment arm.

Two steps, so a person writes every replacement by hand:

    # 1. Write a spec with the passages to edit and empty replacements
    python scripts/report_edits.py template --arm flip --units TCGA-A5-A0GI ...

    # 2. Fill in each "replacement" in the spec, then apply it
    python scripts/report_edits.py apply --arm flip

Arms: flip, reword (same passages as flip), remove, remove_control. Specs and
outputs go in the private issue 8 analysis folder (`inputs/<arm>/`), because
they hold report text. The script prints only counts and problems.
"""

import argparse
import json
from pathlib import Path

from oncotrace_bench.records import ANALYSIS_DIR, REPORTS_PATH, load_reports
from oncotrace_bench.report_edits import check_edits, template_edits, write_arm

ARMS = ["flip", "reword", "remove", "remove_control"]


def main() -> None:
    """Run the `template` or `apply` step for one arm."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["template", "apply"])
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--units", nargs="+", help="patients (template step)")
    parser.add_argument("--reports", type=Path, default=REPORTS_PATH)
    parser.add_argument(
        "--inventory", type=Path, default=ANALYSIS_DIR / "evidence_inventory.json"
    )
    parser.add_argument("--inputs", type=Path, default=ANALYSIS_DIR / "inputs")
    args = parser.parse_args()

    spec_path = args.inputs / f"edit_spec_{args.arm}.json"
    reports = load_reports(args.reports)

    if args.step == "template":
        if spec_path.exists():
            raise SystemExit(f"{spec_path} exists; delete it to start over")
        inventory = json.loads(args.inventory.read_text())
        edits = template_edits(reports, inventory, args.units, args.arm)
        spec_path.write_text(json.dumps(edits, indent=1, ensure_ascii=False))
        spec_path.chmod(0o600)
        print(f"wrote {len(edits)} edits for {len(args.units)} units to {spec_path}")
        return

    edits = json.loads(spec_path.read_text())
    problems = check_edits(reports, edits)
    if problems:
        raise SystemExit("not applied:\n" + "\n".join(problems))
    counts = write_arm(args.reports, edits, args.inputs / args.arm)
    print(f"{args.arm}: {counts['edits']} edits in {counts['units']} units written")


if __name__ == "__main__":
    main()
