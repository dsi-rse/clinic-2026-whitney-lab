"""Compare the old and new myometrial invasion contracts for issue #42.

Reads the issue #42 run folders and writes one timestamped results folder:

- `answers.csv`           one row per patient: the annotation, each temperature-0
                          arm's answer, and whether the answer changed
- `agreement.csv`         per arm, field and patient group: correct / wrong /
                          over-committed / abstained, with the always-commonest
                          baseline
- `changes.csv`           how many patients changed answer between two arms,
                          by patient group (old_a vs old_b is the noise floor)
- `a0gr_repeats.csv`      TCGA-A5-A0GR's 20 temperature-1.0 repeats per contract
- `a0gr_repeat_rows.csv`  one row per A0GR repeat
- `fraction_patients.csv` the four patients with a computable fraction (PR #18)
- `provenance.json`, `README.md`

Patient IDs, labels, counts and character offsets only: no report text.

Run from the repo root (paths are arguments; the runs live wherever you put them):

    PYTHONPATH=src python experiments/issue42_depth_rules/analyze_runs.py \
        --runs-dir <runs folder> --date 2026-11-17 \
        --scan experiments/issue42_depth_rules/results/<scan folder>
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from oncotrace_bench.provenance import build, not_shared_tag
from oncotrace_bench.records import ANNOTATIONS_DIR, load_annotations, load_run

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent

T0_ARMS = ("old_t0_a", "old_t0_b", "new_t0")
REPEATS = 20
REPEAT_ARMS = {
    contract: [f"{contract}_t1_rep{i:02d}" for i in range(1, REPEATS + 1)]
    for contract in ("old", "new")
}
PAIRS = (("old_t0_a", "old_t0_b"), ("old_t0_a", "new_t0"), ("old_t0_b", "new_t0"))

FIELDS = ("myometrial_invasion", "myometrial_invasion_percent", "depth_basis")
UNEVALUABLE = {"not_applicable", "cannot_be_determined"}

A0GJ = "TCGA-A5-A0GJ"
A0GR = "TCGA-A5-A0GR"
# Where A0GR's gross myometrial thickness sits (#26 arithmetic.csv: 2121-2127,
# inside the cited statement 2093-2128). A quote overlapping it means the run
# leaned on the gross thickness.
A0GR_GROSS_THICKNESS = (2093, 2128)
# PR #18's audit: patients where a fraction can be computed from the report.
FRACTION_PATIENTS = ("TCGA-A5-A0GA", "TCGA-2E-A9G8", "TCGA-5B-A90C", "TCGA-A5-A0GW")
# Quotes for one fraction count as the same section when they sit on one page
# within this many characters of each other. A heuristic; see the README.
SAME_SECTION_CHARS = 300
# A worked-out fraction should quote two passages: the depth and the thickness.
FRACTION_QUOTES = 2

ACK_REASON = (
    "OpenRouter run made on a laptop (cluster not used for this work); to be "
    "copied to /net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/"
)


def answer_of(record: dict | None) -> dict | None:
    """Return a record's answer if the model answered, else None."""
    answer = (record or {}).get("answer") or {}
    return answer if answer.get("status") == "answered" else None


def value(answer: dict | None, field: str) -> str:
    """Return one field of an answer, or "" for no answer."""
    return "" if answer is None else str(answer.get(field) or "")


def state(predicted: str, reference: str) -> str:
    """Score one value against the annotation (OncoTrace's four-way split)."""
    if predicted == "":
        return "abstained"
    if predicted == reference:
        return "correct"
    if reference in UNEVALUABLE and predicted not in UNEVALUABLE:
        return "over_committed"
    return "wrong"


def page_of(offset: int, text: str) -> int:
    """Return the page number an offset falls on."""
    return text.count("===== PAGE", 0, offset)


def overlaps(quote: dict, span: tuple[int, int]) -> bool:
    """Whether a quote overlaps a (start, end) range."""
    return quote["start"] < span[1] and span[0] < quote["end"]


def patient_groups(unit: str, annotations: dict, scan: set) -> dict:
    """Return the patient-group flags used to split the tables."""
    annotated = unit in annotations
    percent = (
        annotations[unit]["fields"]["myometrial_invasion_percent"]["value"]
        if annotated
        else ""
    )
    return {
        "annotated": annotated,
        "held_out_aj": annotated and unit.startswith("TCGA-AJ-"),
        "scan_touched": unit in scan,
        # Annotated with a definite half and not flagged by the scan: depth
        # stated plainly enough that neither contract change should move it.
        "unambiguous": annotated
        and percent in ("less_than_50", "fifty_or_greater")
        and unit not in scan,
    }


def build_answers(
    runs: dict, annotations: dict, scan: set, units: list
) -> pd.DataFrame:
    """One row per patient with the annotation and every temperature-0 answer."""
    rows = []
    for unit in units:
        row = {"patient": unit, **patient_groups(unit, annotations, scan)}
        fields = annotations.get(unit, {}).get("fields", {})
        for field in FIELDS:
            row[f"ann_{field}"] = fields.get(field, {}).get("value", "")
        for arm in T0_ARMS:
            answer = answer_of(runs[arm].get(unit))
            for field in FIELDS:
                row[f"{arm}_{field}"] = value(answer, field)
            row[f"{arm}_confidence"] = value(answer, "confidence")
            row[f"{arm}_conflicts"] = len(
                (answer or {}).get("unresolved_conflicts") or []
            )
        for left, right in PAIRS:
            row[f"changed_{left}_vs_{right}"] = any(
                row[f"{left}_{f}"] != row[f"{right}_{f}"]
                for f in ("myometrial_invasion", "myometrial_invasion_percent")
            )
        rows.append(row)
    return pd.DataFrame(rows)


SUBSETS = {
    "annotated_all": lambda df: df["annotated"],
    "development": lambda df: df["annotated"] & ~df["held_out_aj"],
    "held_out_aj": lambda df: df["held_out_aj"],
    "scan_touched_annotated": lambda df: df["annotated"] & df["scan_touched"],
}


def build_agreement(answers: pd.DataFrame) -> pd.DataFrame:
    """Four-way split per arm, field and subset, plus the always-commonest row."""
    annotated = answers[answers["annotated"]]
    rows = []
    for field in FIELDS:
        commonest = annotated[f"ann_{field}"].value_counts().idxmax()
        for subset, pick in SUBSETS.items():
            chosen = answers[pick(answers)]
            arms = [(arm, chosen[f"{arm}_{field}"]) for arm in T0_ARMS]
            arms.append(
                (f"always_{commonest}", pd.Series(commonest, index=chosen.index))
            )
            for arm, predicted in arms:
                counts = Counter(
                    state(p, r)
                    for p, r in zip(predicted, chosen[f"ann_{field}"], strict=True)
                )
                rows.append(
                    {
                        "field": field,
                        "subset": subset,
                        "arm": arm,
                        "patients": len(chosen),
                        **{
                            s: counts[s]
                            for s in ("correct", "wrong", "over_committed", "abstained")
                        },
                    }
                )
    return pd.DataFrame(rows)


def build_changes(answers: pd.DataFrame) -> pd.DataFrame:
    """Patients whose invasion or depth answer changed between two arms."""
    subsets = {
        "all_run": answers.index == answers.index,
        "annotated": answers["annotated"],
        "unambiguous_annotated": answers["unambiguous"],
        "scan_touched": answers["scan_touched"],
        "held_out_aj": answers["held_out_aj"],
    }
    rows = []
    for left, right in PAIRS:
        column = answers[f"changed_{left}_vs_{right}"]
        for subset, mask in subsets.items():
            rows.append(
                {
                    "comparison": f"{left} vs {right}",
                    "subset": subset,
                    "patients": int(mask.sum()),
                    "changed": int((column & mask).sum()),
                    "changed_ids": " ".join(answers[column & mask]["patient"]),
                }
            )
    return pd.DataFrame(rows)


def build_a0gr(runs: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarise A0GR's temperature-1.0 repeats per contract."""
    rows = []
    for contract, arms in REPEAT_ARMS.items():
        for arm in arms:
            answer = answer_of(runs[arm].get(A0GR))
            quotes = (answer or {}).get("quotes") or {}
            all_quotes = [q for qs in quotes.values() for q in qs]
            basis_quotes = quotes.get("depth_basis") or []
            rows.append(
                {
                    "contract": contract,
                    "run": arm,
                    "answered": answer is not None,
                    "myometrial_invasion": value(answer, "myometrial_invasion"),
                    "myometrial_invasion_percent": value(
                        answer, "myometrial_invasion_percent"
                    ),
                    "depth_basis": value(answer, "depth_basis"),
                    "confidence": value(answer, "confidence"),
                    "depth_basis_quotes": len(basis_quotes),
                    "quotes_gross_thickness": any(
                        overlaps(q, A0GR_GROSS_THICKNESS) for q in all_quotes
                    ),
                }
            )
    detail = pd.DataFrame(rows)
    summary = []
    for contract, group in detail.groupby("contract", sort=False):
        answered = group[group["answered"]]
        summary.append(
            {
                "contract": contract,
                "repeats": len(group),
                "answered": len(answered),
                "fifty_or_greater": int(
                    (
                        answered["myometrial_invasion_percent"] == "fifty_or_greater"
                    ).sum()
                ),
                "less_than_50": int(
                    (answered["myometrial_invasion_percent"] == "less_than_50").sum()
                ),
                "percent_other": int(
                    (
                        ~answered["myometrial_invasion_percent"].isin(
                            ["fifty_or_greater", "less_than_50"]
                        )
                    ).sum()
                ),
                "basis_explicit_fraction": int(
                    (answered["depth_basis"] == "explicit_fraction_or_percentage").sum()
                ),
                "explicit_fraction_with_one_quote": int(
                    (
                        (answered["depth_basis"] == "explicit_fraction_or_percentage")
                        & (answered["depth_basis_quotes"] < FRACTION_QUOTES)
                    ).sum()
                ),
                "quotes_gross_thickness": int(answered["quotes_gross_thickness"].sum()),
                "depth_basis_values": " ".join(
                    f"{k}={v}"
                    for k, v in answered["depth_basis"].value_counts().items()
                ),
            }
        )
    return pd.DataFrame(summary), detail


def build_fractions(runs: dict, annotations: dict, reports: dict) -> pd.DataFrame:
    """Before/after answers and depth_basis quotes for the computable fractions."""
    rows = []
    for unit in FRACTION_PATIENTS:
        text = reports[unit]
        fields = annotations.get(unit, {}).get("fields", {})
        for arm in T0_ARMS:
            answer = answer_of(runs[arm].get(unit))
            quotes = sorted(
                ((answer or {}).get("quotes") or {}).get("depth_basis") or [],
                key=lambda q: q["start"],
            )
            pages = sorted({page_of(q["start"], text) for q in quotes})
            gap = (
                max(q["start"] for q in quotes) - min(q["end"] for q in quotes)
                if len(quotes) > 1
                else 0
            )
            rows.append(
                {
                    "patient": unit,
                    "arm": arm,
                    "ann_percent": fields.get("myometrial_invasion_percent", {}).get(
                        "value", ""
                    ),
                    "myometrial_invasion_percent": value(
                        answer, "myometrial_invasion_percent"
                    ),
                    "depth_basis": value(answer, "depth_basis"),
                    "depth_basis_quotes": " ".join(
                        f"{q['start']}-{q['end']}" for q in quotes
                    ),
                    "quote_pages": " ".join(str(p) for p in pages),
                    "same_section": bool(quotes)
                    and len(pages) == 1
                    and gap <= SAME_SECTION_CHARS,
                }
            )
    return pd.DataFrame(rows)


README = """# Issue #42 contract comparison: {name}

Made {created} by `{command}`.

Temperature-0 arms: `old_t0_a`, `old_t0_b` (the same old contract twice, to
measure run-to-run noise) and `new_t0`, each on {n_patients} patients
({n_annotated} annotated, {n_scan_only} more from the extent-wording scan).
A0GR repeats: {repeats} per contract at temperature 1.0. Model and provider are
in `provenance.json` (`runs.*.served_models`, `runs.*.providers`).

## Agreement with the annotations (annotated patients)

One row per arm; columns count patients out of `patients`. `over_committed`
means a definite value where the annotator said `cannot_be_determined` or
`not_applicable`; `abstained` means no accepted answer. `always_*` is the
baseline that always answers the field's commonest annotated value.

{agreement}

## Held-out AJ patients only

Annotated after the contract was written (#27, #29, #37, #40), so the only
subset here that is not optimistic by construction.

{held_out}

## Patients whose invasion or depth answer changed

`old_t0_a vs old_t0_b` is the noise floor: the same contract run twice.
`unambiguous_annotated` = annotated with a definite half and not flagged by
the scan.

{changes}

## TCGA-A5-A0GJ

{a0gj}

## TCGA-A5-A0GR, {repeats} repeats per contract at temperature 1.0

`quotes_gross_thickness` counts repeats that quoted the gross myometrial
thickness statement (offsets {gross}). `explicit_fraction_with_one_quote`
counts repeats that claimed a fraction but quoted only one passage for it.

{a0gr}

## Patients with a computable fraction (PR #18)

`same_section`: the depth_basis quotes sit on one page within
{same_chars} characters of each other (a proximity heuristic, not a parse of
the report's sections).

{fractions}

## Rerun

From the repo root, with the run folders in `<runs folder>`:

    PYTHONPATH=src python {script} --runs-dir <runs folder> --date {date} \\
        --scan {scan}

Takes under a minute and reproduces every CSV here exactly. The runs
themselves are model outputs and will not reproduce bit for bit.
"""


def to_markdown(df: pd.DataFrame) -> str:
    """Render a table as GitHub markdown without the tabulate dependency."""
    header = "| " + " | ".join(df.columns) + " |"
    rule = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.to_numpy()]
    return "\n".join([header, rule, *body])


def parse_args() -> argparse.Namespace:
    """Read the command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--date", required=True, help="date prefix of the run folders")
    parser.add_argument("--scan", type=Path, required=True, help="scan results folder")
    parser.add_argument(
        "--reports",
        type=Path,
        default=REPO_ROOT / "data/endometrial/documents/ucec_pathology_report.jsonl",
    )
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS_DIR)
    parser.add_argument("--out", type=Path, default=EXPERIMENT_DIR / "results")
    parser.add_argument("--label", default="compare")
    return parser.parse_args()


def main() -> None:
    """Build every table and write the results folder."""
    args = parse_args()
    arm_names = [*T0_ARMS, *(a for arms in REPEAT_ARMS.values() for a in arms)]
    run_dirs = {a: args.runs_dir / f"{args.date}_issue42_{a}" for a in arm_names}
    runs = {a: load_run(path) for a, path in run_dirs.items()}
    annotations = load_annotations(args.annotations)
    reports = {}
    with args.reports.open() as f:
        for line in f:
            row = json.loads(line)
            reports[row["unit"]] = row["text"]
    roster = EXPERIMENT_DIR / "rosters" / "roster_compare.csv"
    units = pd.read_csv(roster)["unit"].tolist()
    scan = set(pd.read_csv(args.scan / "extent_patients.csv")["patient"])

    answers = build_answers(runs, annotations, scan, units)
    agreement = build_agreement(answers)
    changes = build_changes(answers)
    a0gr, a0gr_rows = build_a0gr(runs)
    fractions = build_fractions(runs, annotations, reports)

    record = build(
        inputs={
            "roster_compare": roster,
            "roster_a0gr": EXPERIMENT_DIR / "rosters" / "roster_a0gr.csv",
            "scan_patients": args.scan / "extent_patients.csv",
            "contract_old": EXPERIMENT_DIR / "contracts" / "old.yaml",
            "contract_new": EXPERIMENT_DIR / "contracts" / "new.yaml",
            **{
                f"config_{p.stem}": p
                for p in sorted((EXPERIMENT_DIR / "configs").glob("*.yaml"))
            },
        },
        runs=run_dirs,
        repo_root=REPO_ROOT,
        acknowledged={not_shared_tag(a): ACK_REASON for a in arm_names},
        script=str(Path(__file__).relative_to(REPO_ROOT)),
        command=" ".join(sys.argv),
        annotation_files=len(annotations),
    )

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = args.out / f"{stamp}_{args.label}"
    out.mkdir(parents=True)
    answers.to_csv(out / "answers.csv", index=False)
    agreement.to_csv(out / "agreement.csv", index=False)
    changes.to_csv(out / "changes.csv", index=False)
    a0gr.to_csv(out / "a0gr_repeats.csv", index=False)
    a0gr_rows.to_csv(out / "a0gr_repeat_rows.csv", index=False)
    fractions.to_csv(out / "fraction_patients.csv", index=False)
    (out / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")

    a0gj_columns = [
        "patient",
        "ann_myometrial_invasion",
        "ann_myometrial_invasion_percent",
    ]
    for arm in T0_ARMS:
        a0gj_columns += [
            f"{arm}_myometrial_invasion",
            f"{arm}_myometrial_invasion_percent",
            f"{arm}_depth_basis",
        ]
    (out / "README.md").write_text(
        README.format(
            name=out.name,
            created=stamp,
            command=" ".join(sys.argv),
            n_patients=len(answers),
            n_annotated=int(answers["annotated"].sum()),
            n_scan_only=int((answers["scan_touched"] & ~answers["annotated"]).sum()),
            repeats=REPEATS,
            agreement=to_markdown(agreement[agreement["subset"] == "annotated_all"]),
            held_out=to_markdown(agreement[agreement["subset"] == "held_out_aj"]),
            changes=to_markdown(changes.drop(columns="changed_ids")),
            a0gj=to_markdown(
                answers[answers["patient"] == A0GJ][a0gj_columns].T.reset_index()
            ),
            gross=f"{A0GR_GROSS_THICKNESS[0]}-{A0GR_GROSS_THICKNESS[1]}",
            a0gr=to_markdown(a0gr),
            same_chars=SAME_SECTION_CHARS,
            fractions=to_markdown(fractions),
            script=str(Path(__file__).relative_to(REPO_ROOT)),
            date=args.date,
            scan=str(args.scan.relative_to(REPO_ROOT))
            if args.scan.is_absolute()
            else args.scan,
        )
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
