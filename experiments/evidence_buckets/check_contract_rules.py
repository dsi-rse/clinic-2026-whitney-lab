"""Check offline that the evidence-buckets contract accepts and refuses what it should.

No model and no reports: each case is a made-up submission passed to OncoTrace's
own `check_answer`, which is what `submit` runs before it records an answer.

Run from the clinic repo root:
    PYTHONPATH=src:<oncotrace clone> python experiments/evidence_buckets/check_contract_rules.py
"""

import argparse
from pathlib import Path

import yaml
from oncotrace.records import Span
from oncotrace.task import check_answer, load_task

QUOTE = [Span("pathology_report", "report", 0, 10)]

# A complete, admissible "present, less than half, stated outright" answer.
# Each case below changes only the fields it names.
BASE = {
    "specimen_type": "hysterectomy",
    "myometrial_invasion_percent": "less_than_50",
    "depth_basis": "explicit_fraction_or_percentage",
    "adenomyosis_relation": "not_mentioned",
    "myometrial_invasion_evidence": "explicit",
    "myometrial_invasion_percent_evidence": "explicit",
}

# (description, label, field changes, answers left without quotes, expected signature)
CASES = [
    ("explicit present answer", "present", {}, [], None),
    (
        "implied depth",
        "present",
        {"myometrial_invasion_percent_evidence": "implied_medium"},
        [],
        None,
    ),
    (
        "uncertain invasion, depth not_applicable",
        "uncertain",
        {
            "myometrial_invasion_percent": "not_applicable",
            "myometrial_invasion_evidence": "uncertain",
            "myometrial_invasion_percent_evidence": "not_applicable",
        },
        [],
        None,
    ),
    (
        "not present: no quotes needed",
        "cannot_be_determined",
        {
            "myometrial_invasion_percent": "cannot_be_determined",
            "depth_basis": "none_stated",
            "myometrial_invasion_evidence": "not_present",
            "myometrial_invasion_percent_evidence": "not_present",
        },
        ["myometrial_invasion", "myometrial_invasion_percent", "depth_basis"],
        None,
    ),
    (
        "uncertain depth under present",
        "present",
        {
            "myometrial_invasion_percent": "uncertain",
            "myometrial_invasion_percent_evidence": "uncertain",
        },
        [],
        None,
    ),
    # Refusals
    (
        "uncertain without a quote",
        "uncertain",
        {
            "myometrial_invasion_percent": "not_applicable",
            "myometrial_invasion_evidence": "uncertain",
            "myometrial_invasion_percent_evidence": "not_applicable",
        },
        ["myometrial_invasion"],
        "myometrial_invasion_quote_missing",
    ),
    (
        "present labelled uncertain",
        "present",
        {"myometrial_invasion_evidence": "uncertain"},
        [],
        "definite_invasion_needs_explicit_or_implied",
    ),
    (
        "uncertain labelled explicit",
        "uncertain",
        {
            "myometrial_invasion_percent": "not_applicable",
            "myometrial_invasion_percent_evidence": "not_applicable",
        },
        [],
        "uncertain_invasion_is_uncertain",
    ),
    (
        "cannot_be_determined labelled explicit",
        "cannot_be_determined",
        {
            "myometrial_invasion_percent": "cannot_be_determined",
            "myometrial_invasion_percent_evidence": "not_present",
        },
        [],
        "undetermined_invasion_is_not_present",
    ),
    (
        "cannot_be_determined label with not_applicable depth",
        "cannot_be_determined",
        {
            "myometrial_invasion_percent": "not_applicable",
            "myometrial_invasion_evidence": "not_present",
            "myometrial_invasion_percent_evidence": "not_applicable",
        },
        [],
        "undetermined_invasion_has_undetermined_depth",
    ),
    (
        "definite depth labelled not_present",
        "present",
        {"myometrial_invasion_percent_evidence": "not_present"},
        [],
        "definite_depth_needs_explicit_or_implied",
    ),
    (
        "uncertain depth labelled implied",
        "present",
        {
            "myometrial_invasion_percent": "uncertain",
            "myometrial_invasion_percent_evidence": "implied_low",
        },
        [],
        "uncertain_depth_is_uncertain",
    ),
    (
        "not_applicable depth labelled explicit",
        "not_identified",
        {"myometrial_invasion_percent": "not_applicable"},
        [],
        "inapplicable_depth_is_not_applicable",
    ),
]


def main() -> None:
    """Run every case and exit nonzero if any behaves unexpectedly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(__file__).parent / "endo_myometrial_invasion_evidence.yaml",
    )
    arguments = parser.parse_args()
    task = load_task(yaml.safe_load(arguments.contract.read_text()))

    failures = 0
    for description, label, changes, unquoted, expected in CASES:
        fields = {**BASE, **changes}
        quotes = {
            name: QUOTE
            for name in (task.label_field, *fields)
            if name not in unquoted and name not in task.no_quote_fields
        }
        violation = check_answer(
            task, label, fields, quotes, {"unresolved_conflicts": []}
        )
        got = violation.signature if violation else None
        ok = got == expected
        failures += not ok
        print(
            f"{'ok  ' if ok else 'FAIL'} {description}: expected {expected}, got {got}"
        )
    print(f"{len(CASES) - failures} of {len(CASES)} cases behave as expected")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
