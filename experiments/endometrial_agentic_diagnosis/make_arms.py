"""Write the one-factor-at-a-time configs for the issue 16 experiments.

Every arm is `base.yaml` with exactly one setting changed (the rule arm changes one
line of a copy of the task contract instead). The script checks that, so a stray edit
cannot slip in, and prints what each arm changes.

Example:
    python experiments/endometrial_agentic_diagnosis/make_arms.py
"""

import argparse
import difflib
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
TASK = EXPERIMENT_DIR.parent.parent / "tasks" / "endo_myometrial_invasion.yaml"
RULE_LINE = "    must_be_subset_of: [depth_evidence]\n"

# arm name -> (setting changed, line in base.yaml, replacement or None to add after it)
SETTING_ARMS = {
    "calls6": ("model calls 24 -> 6", "  model_calls: 24\n", "  model_calls: 6\n"),
    "calls12": ("model calls 24 -> 12", "  model_calls: 24\n", "  model_calls: 12\n"),
    "tokens16k": (
        "reply cap 8192 -> 16384 tokens",
        "  max_completion_tokens: 8192\n",
        "  max_completion_tokens: 16384\n",
    ),
    "compact": (
        "compact rejected submissions on",
        "  request_timeout_seconds: 1800\n",
        "  request_timeout_seconds: 1800\n  compact_rejected_submissions: true\n",
    ),
    "rescue": (
        "roster: only the patients that failed in issue 9",
        "roster: roster_annotated50.csv\n",
        "roster: roster_failed_in_issue9.csv\n",
    ),
    "read6k": (
        "read size 18000 -> 6000 chars",
        "  max_read_chars: 18000\n",
        "  max_read_chars: 6000\n",
    ),
}
RULE_ARM = "norule"
RULE_TASK_NAME = "task_no_depth_subset.yaml"


def changed_lines(before: str, after: str) -> list[str]:
    """The lines that differ between two texts, as +/- lines."""
    diff = difflib.unified_diff(
        before.splitlines(), after.splitlines(), lineterm="", n=0
    )
    return [
        line for line in diff if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]


def main() -> None:
    """Write the arm configs and check each differs from the base in one place."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.parse_args()
    base = (EXPERIMENT_DIR / "base.yaml").read_text(encoding="utf-8")
    report = []
    for name, (what, old, new) in SETTING_ARMS.items():
        if base.count(old) != 1:
            raise SystemExit(f"base.yaml must contain exactly one {old.strip()!r}")
        text = base.replace(old, new)
        (EXPERIMENT_DIR / f"arm_{name}.yaml").write_text(text, encoding="utf-8")
        report.append((name, what, changed_lines(base, text)))

    task_text = TASK.read_text(encoding="utf-8")
    if task_text.count(RULE_LINE) != 1:
        raise SystemExit(
            "the task contract changed: expected one quantified_depth subset rule"
        )
    task_copy = task_text.replace(RULE_LINE, "")
    (EXPERIMENT_DIR / RULE_TASK_NAME).write_text(task_copy, encoding="utf-8")
    text = base.replace(
        "task: ../../tasks/endo_myometrial_invasion.yaml", f"task: {RULE_TASK_NAME}"
    )
    (EXPERIMENT_DIR / f"arm_{RULE_ARM}.yaml").write_text(text, encoding="utf-8")
    report.append(
        (RULE_ARM, "drop the quantified_depth subset rule", changed_lines(base, text))
    )
    report.append(
        (
            "(task copy)",
            "one line removed from the contract",
            changed_lines(task_text, task_copy),
        )
    )

    for name, what, lines in report:
        print(f"{name}: {what}")
        for line in lines:
            print(f"    {line}")
        if len(lines) > 2:  # noqa: PLR2004 - one removed line and one added line at most
            raise SystemExit(f"{name} changes more than one setting")


if __name__ == "__main__":
    main()
