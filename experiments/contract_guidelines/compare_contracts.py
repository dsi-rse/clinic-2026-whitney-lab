"""Check and score the three contracts of the contract-guidelines test (#44).

Writes a new results folder holding:
- offline checks of each contract, made by script (does it load, undeclared
  values in rules, annotation values it doesn't allow, undeclared names in the
  instructions, values with no definition, 7-word runs shared with reports);
- the hand-scored known gaps from `inputs/gap_scores.csv`, summed;
- if runs are given, agreement with the annotations for invasion and depth,
  per run and averaged per arm, with the always-the-commonest baseline, and
  refusals by rule.

No report text is written: only names, counts, patient IDs and reason codes.

Example (offline only, then with runs):
    python experiments/contract_guidelines/compare_contracts.py \
        --oncotrace ../oncotrace --label offline
    python experiments/contract_guidelines/compare_contracts.py \
        --oncotrace ../oncotrace --label runs \
        --run old=runs/X_old/rep1 --run old=runs/X_old/rep2 ...
"""

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import yaml

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from oncotrace_bench import provenance, traceview_summary  # noqa: E402
from oncotrace_bench.records import load_annotations  # noqa: E402

ARMS = ("old", "unguided", "guided")
CONTRACTS = {arm: EXPERIMENT_DIR / "contracts" / f"{arm}.yaml" for arm in ARMS}
SCORED_ROSTER = (
    REPO_ROOT / "experiments" / "endometrial_baseline_full" / "roster_annotated66.csv"
)
EXAMPLE_ROSTER = EXPERIMENT_DIR / "inputs" / "example_reports.csv"
KNOWN_GAPS = EXPERIMENT_DIR / "inputs" / "known_gaps.csv"
GAP_SCORES = EXPERIMENT_DIR / "inputs" / "gap_scores.csv"
REPORTS = (
    REPO_ROOT / "data" / "endometrial" / "documents" / "ucec_pathology_report.jsonl"
)
# The two answers scored, by the name the annotations use.
FIELDS = {"invasion": "myometrial_invasion", "depth": "myometrial_invasion_percent"}
# Names OncoTrace itself puts in front of the model, so the instructions may use them.
RUNTIME_NAMES = {"document_chars"}
NGRAM = 7


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    """Write one table."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def words(text: str) -> list[str]:
    """Lower-case word tokens, for the 7-word overlap check."""
    return re.findall(r"[a-z0-9]+", text.lower())


def ngrams(text: str) -> set[str]:
    """Every run of NGRAM consecutive words in a text."""
    tokens = words(text)
    return {" ".join(tokens[i : i + NGRAM]) for i in range(len(tokens) - NGRAM + 1)}


def declared_values(contract: dict) -> dict[str, list[str]]:
    """Field name -> allowed values, for the label and every extra field."""
    label = contract["label"]
    values = {label.get("field", "label"): list(label["values"])}
    for field in contract.get("extra_fields", []):
        values[field["name"]] = list(field["values"])
    return values


def undeclared_rule_values(contract: dict) -> list[str]:
    """Values named in a rule or in no_quote_values that no field declares."""
    values = declared_values(contract)
    label_field = contract["label"].get("field", "label")
    every_value = {value for field in values.values() for value in field}
    problems = []
    for rule in contract.get("rules", []):
        named = [(label_field, value) for value in rule.get("when_label", [])]
        for key in ("when_field", "require_field"):
            if rule.get(key):
                field = rule[key]["field"]
                named += [(field, value) for value in rule[key]["values"]]
        for field, value in named:
            if value not in values.get(field, []):
                problems.append(f"{rule['signature']}:{field}={value}")
    for value in contract.get("no_quote_values", []):
        if value not in every_value:
            problems.append(f"no_quote_values:{value}")
    return problems


def annotation_problems(
    contract: dict, annotations: dict, units: list[str]
) -> list[str]:
    """Annotated values the contract doesn't allow, as 'field=value' with a count."""
    values = declared_values(contract)
    found = Counter()
    for unit in units:
        fields = annotations[unit]["fields"]
        for field, allowed in values.items():
            if field not in fields:
                found[f"{field}=(field missing)"] += 1
            elif fields[field]["value"] not in allowed:
                found[f"{field}={fields[field]['value']!r}"] += 1
    return [f"{item} x{count}" for item, count in sorted(found.items())]


def undeclared_instruction_names(contract: dict) -> list[str]:
    """snake_case names in the instructions that the contract doesn't declare."""
    values = declared_values(contract)
    declared = set(values) | {value for field in values.values() for value in field}
    declared |= set(contract.get("list_fields", [])) | RUNTIME_NAMES
    names = set(
        re.findall(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b", contract.get("instructions", ""))
    )
    return sorted(names - declared)


def undefined_values(contract: dict, text: str) -> list[str]:
    """Values never named in the instructions and with no comment beside or above them.

    A heuristic: a comment can exist and still not define a value, so this is a
    list for a person to read, not a verdict.
    """
    instructions = contract.get("instructions", "")
    lines = text.splitlines()
    missing = []
    for field, field_values in declared_values(contract).items():
        for value in field_values:
            if re.search(rf"\b{re.escape(value)}\b", instructions):
                continue
            commented = False
            for index, line in enumerate(lines):
                if re.match(rf"\s*-\s*{re.escape(value)}\s*(#.*)?$", line):
                    above = lines[index - 1].strip() if index else ""
                    commented = "#" in line or above.startswith("#")
                    break
            if not commented:
                missing.append(f"{field}:{value}")
    return missing


def report_texts(units: set[str]) -> list[str]:
    """Report text for the given patients, kept in memory only."""
    texts = []
    with REPORTS.open() as handle:
        for line in handle:
            record = json.loads(line)
            if record["unit"] in units:
                texts.append(record["text"])
    return texts


def shared_ngrams(contract_text: str, reports: list[str]) -> int:
    """How many of the contract's 7-word runs occur in any of the reports."""
    grams = ngrams(contract_text)
    report_grams = set().union(*(ngrams(text) for text in reports))
    return len(grams & report_grams)


def offline_rows(
    annotations: dict, scored: list[str], examples: list[str]
) -> list[list]:
    """One row per contract and check."""
    from oncotrace.task import load_task

    scored_texts = report_texts(set(scored))
    example_texts = report_texts(set(examples))
    rows = []
    for arm, path in CONTRACTS.items():
        text = path.read_text()
        contract = yaml.safe_load(text)
        try:
            load_task(contract)
            load_error = []
        except (ValueError, KeyError, TypeError) as error:
            load_error = [type(error).__name__ + ": " + str(error)[:120]]
        checks = {
            "fails_to_load": load_error,
            "undeclared_rule_values": undeclared_rule_values(contract),
            "annotation_values_not_allowed": annotation_problems(
                contract, annotations, scored
            ),
            "undeclared_instruction_names": undeclared_instruction_names(contract),
            "values_without_definition": undefined_values(contract, text),
        }
        for check, items in checks.items():
            count = (
                sum(int(item.rsplit(" x", 1)[1]) for item in items)
                if check.startswith("annotation")
                else len(items)
            )
            rows.append([arm, check, count, "; ".join(items)])
        rows.append(
            [
                arm,
                "7word_runs_shared_with_scored_reports",
                shared_ngrams(text, scored_texts),
                "",
            ]
        )
        rows.append(
            [
                arm,
                "7word_runs_shared_with_example_reports",
                shared_ngrams(text, example_texts),
                "",
            ]
        )
    return rows


def gap_rows() -> tuple[list[list], list[str]]:
    """Hand scores per contract and gap, plus a total row per contract."""
    gaps = [row["gap"] for row in csv.DictReader(KNOWN_GAPS.open())]
    if not GAP_SCORES.exists():
        return [], gaps
    scores = defaultdict(dict)
    for row in csv.DictReader(GAP_SCORES.open()):
        if row["gap"] not in gaps or row["score"] not in {"0", "0.5", "1"}:
            raise SystemExit(f"bad row in {GAP_SCORES.name}: {row}")
        scores[row["contract"]][row["gap"]] = float(row["score"])
    rows = []
    for arm in ARMS:
        if set(scores[arm]) != set(gaps):
            raise SystemExit(f"{GAP_SCORES.name} must score every gap for {arm}")
        rows.append(
            [arm, *[scores[arm][gap] for gap in gaps], sum(scores[arm].values())]
        )
    return rows, gaps


def run_rows(
    runs: list[tuple[str, Path]], annotations: dict, scored: list[str]
) -> tuple:
    """Agreement per run and field, refusals per run, and the commonest baseline.

    Also returns each patient's answer and outcome per run, keyed by
    (field name, patient) and then by run name (arm_1, arm_2, ...).
    """
    import scoring

    per_run, refusals = [], []
    per_patient = defaultdict(dict)
    arm_counts = Counter()
    for index, (arm, run_dir) in enumerate(runs):
        arm_counts[arm] += 1
        run_name = f"{arm}_{arm_counts[arm]}"
        views, _ = traceview_summary.load_views(run_dir, CONTRACTS[arm])
        views = [view for view in views if view.unit in set(scored)]
        outcomes = Counter(traceview_summary.outcome_of(view) for view in views)
        refused = Counter()
        for view in views:
            refused += traceview_summary.refusal_counts(view)
        calls = sum(view.record.get("model_calls", 0) for view in views)
        refusals += [
            [arm, index, run_dir.name, sig, n] for sig, n in sorted(refused.items())
        ]
        for name, field in FIELDS.items():
            predicted, errors = scoring.predictions(
                views, "" if name == "invasion" else field
            )
            units = sorted(set(predicted) - errors)
            reference = {u: annotations[u]["fields"][field]["value"] for u in units}
            state_of = {
                u: scoring.agreement_state(predicted[u], reference[u]) for u in units
            }
            states = Counter(state_of.values())
            for unit in scored:
                per_patient[(name, unit)][run_name] = (
                    predicted.get(unit, ""),
                    state_of.get(unit, "no_score"),
                )
            per_run.append(
                [
                    arm,
                    index,
                    run_dir.name,
                    name,
                    len(views),
                    len(errors),
                    outcomes[traceview_summary.NO_ANSWER],
                    calls,
                    states["correct"],
                    states["wrong"],
                    states["over_committed"],
                    states["abstained"],
                ]
            )
    baseline = []
    for name, field in FIELDS.items():
        values = Counter(annotations[u]["fields"][field]["value"] for u in scored)
        value, hits = values.most_common(1)[0]
        baseline.append([name, value, len(scored), hits])
    return per_run, refusals, baseline, per_patient


def patient_rows(
    per_patient: dict, annotations: dict, run_names: list[str]
) -> list[list]:
    """One row per field and patient: the annotation, then answer and outcome per run."""
    rows = []
    for (name, unit), by_run in sorted(per_patient.items()):
        reference = annotations[unit]["fields"][FIELDS[name]]["value"]
        row = [name, unit, reference]
        for run_name in run_names:
            row += list(by_run.get(run_name, ("", "no_score")))
        rows.append(row)
    return rows


def change_rows(per_patient: dict, run_names: list[str]) -> list[list]:
    """Per arm and field, patients that moved against old in every run.

    better: correct in each of the arm's runs and in neither old run.
    worse: correct in each old run and in none of the arm's runs.
    same_in_all_runs: the outcome is the same in every run of every arm.
    """
    rows = []
    old_runs = [r for r in run_names if r.startswith("old_")]
    for arm in ARMS:
        arm_runs = [r for r in run_names if r.startswith(f"{arm}_")]
        if arm == "old" or not arm_runs or not old_runs:
            continue
        for name in FIELDS:
            better, worse, steady = [], [], 0
            for (field_name, unit), by_run in sorted(per_patient.items()):
                if field_name != name:
                    continue
                old_ok = [by_run[r][1] == "correct" for r in old_runs]
                arm_ok = [by_run[r][1] == "correct" for r in arm_runs]
                if all(arm_ok) and not any(old_ok):
                    better.append(unit)
                if all(old_ok) and not any(arm_ok):
                    worse.append(unit)
                if len({by_run[r][1] for r in run_names}) == 1:
                    steady += 1
            rows.append(
                [
                    arm,
                    name,
                    len(better),
                    len(worse),
                    steady,
                    " ".join(better),
                    " ".join(worse),
                ]
            )
    return rows


def mean_rows(per_run: list[list]) -> list[list]:
    """Per arm and field: the mean, lowest and highest count over its runs."""
    grouped = defaultdict(list)
    for row in per_run:
        grouped[(row[0], row[3])].append(row)
    rows = []
    for arm in ARMS:
        for name in FIELDS:
            group = grouped.get((arm, name))
            if not group:
                continue
            row = [arm, name, len(group)]
            for column in (8, 10, 11):  # correct, over_committed, abstained
                counts = [item[column] for item in group]
                row += [f"{statistics.mean(counts):.1f}", min(counts), max(counts)]
            rows.append(row)
    return rows


def main() -> None:
    """Run the offline checks, and score the runs if any are given."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--oncotrace", type=Path, required=True, help="OncoTrace clone")
    parser.add_argument("--label", required=True, help="suffix for the results folder")
    parser.add_argument(
        "--run", action="append", default=[], help="ARM=RUN_FOLDER, repeatable"
    )
    parser.add_argument("--results", type=Path, default=EXPERIMENT_DIR / "results")
    parser.add_argument("--acknowledge", action="append", default=[], help="TAG=REASON")
    args = parser.parse_args()

    traceview_summary.add_traceview_to_path(args.oncotrace.resolve())
    runs = []
    for item in args.run:
        arm, path = item.split("=", 1)
        if arm not in ARMS:
            raise SystemExit(f"unknown arm {arm}")
        runs.append((arm, Path(path).resolve()))
    scored = traceview_summary.read_roster(SCORED_ROSTER)
    examples = traceview_summary.read_roster(EXAMPLE_ROSTER)
    annotations = load_annotations()

    run_names = Counter()
    run_paths = {}
    for arm, path in runs:
        run_names[arm] += 1
        run_paths[f"{arm}_{run_names[arm]}"] = path
    inputs = {f"contract_{arm}": path for arm, path in CONTRACTS.items()}
    inputs |= {
        "scored_roster": SCORED_ROSTER,
        "example_reports": EXAMPLE_ROSTER,
        "known_gaps": KNOWN_GAPS,
    }
    if GAP_SCORES.exists():
        inputs["gap_scores"] = GAP_SCORES
    record = provenance.build(
        inputs=inputs,
        runs=run_paths,
        repo_root=REPO_ROOT,
        analysis_repos={"oncotrace": args.oncotrace.resolve()},
        acknowledged=dict(item.split("=", 1) for item in args.acknowledge) or None,
        arguments=sys.argv[1:],
    )

    offline = offline_rows(annotations, scored, examples)
    gaps, gap_names = gap_rows()
    per_run, refusals, baseline, per_patient = (
        run_rows(runs, annotations, scored) if runs else ([], [], [], {})
    )
    names = list(run_paths)

    stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    out = args.results / f"{stamp}_{args.label}"
    out.mkdir(parents=True, exist_ok=False)
    (out / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    write_csv(
        out / "offline_checks.csv", ["contract", "check", "count", "items"], offline
    )
    readme = [
        f"# Contract-guidelines test: {args.label}",
        "",
        f"Made {stamp} UTC by `experiments/contract_guidelines/compare_contracts.py "
        + " ".join(sys.argv[1:])
        + "`. Commits and hashes are in `provenance.json`.",
        "",
        "- `offline_checks.csv`: one row per contract and check, made by script. "
        "`items` names the values or names found; report text is never written.",
    ]
    if gaps:
        write_csv(out / "known_gaps.csv", ["contract", *gap_names, "total"], gaps)
        readme.append(
            "- `known_gaps.csv`: hand scores from `inputs/gap_scores.csv` "
            "(1 fixed, 0.5 partly, 0 not), summed. The reasons are in that file."
        )
    if per_run:
        header = [
            "arm",
            "run_index",
            "run",
            "field",
            "patients",
            "server_errors",
            "no_answer",
            "model_calls",
            "correct",
            "wrong",
            "over_committed",
            "abstained",
        ]
        write_csv(out / "agreement_per_run.csv", header, per_run)
        write_csv(
            out / "agreement_by_arm.csv",
            [
                "arm",
                "field",
                "runs",
                "correct_mean",
                "correct_min",
                "correct_max",
                "over_committed_mean",
                "over_committed_min",
                "over_committed_max",
                "abstained_mean",
                "abstained_min",
                "abstained_max",
            ],
            mean_rows(per_run),
        )
        write_csv(
            out / "baseline_commonest.csv",
            ["field", "commonest_annotation", "patients", "correct"],
            baseline,
        )
        write_csv(
            out / "refusals.csv",
            ["arm", "run_index", "run", "signature", "count"],
            refusals,
        )
        write_csv(
            out / "outcomes_per_patient.csv",
            ["field", "patient", "annotation"]
            + [f"{r}_{part}" for r in names for part in ("answer", "outcome")],
            patient_rows(per_patient, annotations, names),
        )
        write_csv(
            out / "changes_vs_old.csv",
            [
                "arm",
                "field",
                "better",
                "worse",
                "same_in_all_runs",
                "better_patients",
                "worse_patients",
            ],
            change_rows(per_patient, names),
        )
        readme += [
            "- `agreement_per_run.csv`: per run and field, patients out of the scored "
            "roster: correct, wrong, over-committed (a definite answer where the annotation "
            "says not applicable or cannot be determined) and abstained (no answer).",
            "- `agreement_by_arm.csv`: the same counts averaged over each arm's runs, with "
            "the lowest and highest run.",
            "- `baseline_commonest.csv`: what always answering the commonest annotation scores.",
            "- `refusals.csv`: OncoTrace's refusals by rule signature, per run.",
            "- `outcomes_per_patient.csv`: per field and patient, the annotation, then "
            "each run's answer and outcome (correct, wrong, over_committed, abstained; "
            "no_score for a server error).",
            "- `changes_vs_old.csv`: per arm and field, patients `better` (correct in each "
            "of the arm's runs, in neither `old` run) and `worse` (the reverse), with their "
            "IDs; `same_in_all_runs` counts patients with one outcome across all runs.",
        ]
    (out / "README.md").write_text("\n".join(readme) + "\n")
    print(out)


if __name__ == "__main__":
    main()
