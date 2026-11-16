"""Compare OpenRouter providers of GLM-5.3-Flash on the same 10 patients.

Each arm is one provider, run several times. For every arm this writes how many
patient runs were answered, how many patients got the same answer in every
repeat, the tokens used and what they cost, and, per patient, the answer in each
repeat beside the cluster's 20-repeat tally for the same patient. No report text
is written, only patient IDs, labels and counts.

Example, from the clinic repo root:
    PYTHONPATH=src python experiments/openrouter_providers/compare_providers.py \
        --arm wafer_us=runs/2026-11-16_openrouter_providers_wafer_us \
        --arm darkbloom_fp4=runs/2026-11-16_openrouter_providers_darkbloom_fp4 \
        --arm morph_fp8=runs/2026-11-16_openrouter_providers_morph_fp8 \
        --not-shared "on CRI until the DSI cluster is back"
"""

import argparse
import csv
import json
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

from oncotrace_bench.provenance import build, not_shared_tag, sha256
from oncotrace_bench.records import load_run

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
ROSTER = REPO_ROOT / "experiments/endometrial_determinism/roster_followup10.csv"
TASK = REPO_ROOT / "tasks/endo_myometrial_invasion.yaml"
# The cluster's 20 repeats of these 10 patients. They used the task contract from
# before PR 48, so they are a reference for how much the answers vary, not a
# like-for-like control.
CLUSTER_TABLE = (
    REPO_ROOT / "experiments/endometrial_determinism/results/"
    "2026-11-02_095348_agentic_0b6f404_10x20/per_patient.csv"
)
ENDPOINTS_URL = "https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints"
LABEL_KEY = "myometrial_invasion"
DEPTH_KEY = "myometrial_invasion_percent"
NO_ANSWER = "NO_ANSWER"


def outcome(record: dict) -> str:
    """'invasion/depth', or NO_ANSWER, as in endometrial_determinism."""
    answer = record.get("answer")
    if isinstance(answer, dict) and LABEL_KEY in answer:
        return f"{answer[LABEL_KEY]}/{answer.get(DEPTH_KEY)}"
    return NO_ANSWER


def responses(record: dict) -> list[dict]:
    """The model replies in one unit record."""
    return [e for e in record.get("events") or [] if e.get("kind") == "model_response"]


def provider_slug(config: Path) -> str:
    """The one provider an arm's config pins."""
    text = config.read_text()
    line = next(line for line in text.splitlines() if "order: [" in line)
    return line.split("[", 1)[1].split("]", 1)[0].strip()


def fetch_prices(path: Path) -> None:
    """Save OpenRouter's current price list for this model as a CSV."""
    # A fixed https URL, so the scheme check ruff asks for is already met.
    with urllib.request.urlopen(ENDPOINTS_URL, timeout=30) as response:  # noqa: S310
        endpoints = json.load(response)["data"]["endpoints"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "provider",
                "quantization",
                "usd_per_million_input",
                "usd_per_million_output",
            ]
        )
        for e in sorted(endpoints, key=lambda e: e["tag"]):
            writer.writerow(
                [
                    e["tag"],
                    e.get("quantization"),
                    round(float(e["pricing"]["prompt"]) * 1e6, 6),
                    round(float(e["pricing"]["completion"]) * 1e6, 6),
                ]
            )


def read_prices(path: Path) -> dict[str, dict]:
    """Provider -> its row of the price table."""
    with path.open(encoding="utf-8") as handle:
        return {row["provider"]: row for row in csv.DictReader(handle)}


def cluster_tallies(path: Path) -> dict[str, str]:
    """Patient -> 'outcome xN; ...' over the cluster's 20 repeats, most common first."""
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        row["patient"]: "; ".join(
            f"{name} x{count}"
            for name, count in Counter(
                row["outcome_per_run"].split(" | ")
            ).most_common()
        )
        for row in rows
    }


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    """Write one table with LF line ends, so a rerun is byte-identical."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    """Read every arm's repeats and write the tables."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--arm",
        action="append",
        required=True,
        metavar="NAME=FOLDER",
        help="an arm's config name and the folder holding its rep1, rep2, ...",
    )
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    parser.add_argument("--label", default="", help="suffix for the result folder name")
    parser.add_argument(
        "--prices", type=Path, help="a saved prices.csv; default: fetch today's"
    )
    parser.add_argument(
        "--not-shared",
        metavar="REASON",
        help="the run folders are not on the shared cluster yet: say where they are",
    )
    arguments = parser.parse_args()

    with ROSTER.open(encoding="utf-8") as handle:
        patients = [row["unit"] for row in csv.DictReader(handle)]
    arms = {}
    for item in arguments.arm:
        name, folder = item.split("=", 1)
        reps = sorted(Path(folder).glob("rep*"), key=lambda p: int(p.name[3:]))
        arms[name] = {
            "config": EXPERIMENT_DIR / "configs" / f"{name}.yaml",
            "reps": reps,
            "runs": [load_run(rep) for rep in reps],
        }

    run_folders = {
        f"{name}_{rep.name}": rep for name, arm in arms.items() for rep in arm["reps"]
    }
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = arguments.results_dir / (
        stamp + (f"_{arguments.label}" if arguments.label else "")
    )
    inputs = {f"config_{name}": arm["config"] for name, arm in arms.items()}
    inputs |= {"roster": ROSTER, "cluster_reference": CLUSTER_TABLE}
    if arguments.prices:
        inputs["prices"] = arguments.prices
    acknowledged = {}
    if arguments.not_shared:
        acknowledged = {
            not_shared_tag(name): arguments.not_shared for name in run_folders
        }
    # Before the folder exists, so it is not recorded as uncommitted.
    provenance = build(
        inputs=inputs,
        runs=run_folders,
        repo_root=REPO_ROOT,
        task=TASK,
        acknowledged=acknowledged,
        arms={name: provider_slug(arm["config"]) for name, arm in arms.items()},
    )
    out.mkdir(parents=True)

    prices_path = out / "prices.csv"
    if arguments.prices:
        prices_path.write_bytes(arguments.prices.read_bytes())
    else:
        fetch_prices(prices_path)
    provenance["prices"] = {"path": str(prices_path), "sha256": sha256(prices_path)}
    prices = read_prices(prices_path)
    reference = cluster_tallies(CLUSTER_TABLE)

    arm_rows, per_patient = [], {patient: [patient] for patient in patients}
    modal = {patient: [] for patient in patients}
    for name, arm in arms.items():
        slug = provider_slug(arm["config"])
        records = [run[p] for run in arm["runs"] for p in patients if p in run]
        replies = [reply for record in records for reply in responses(record)]
        tokens_in = sum(reply.get("prompt_tokens") or 0 for reply in replies)
        tokens_out = sum(reply.get("completion_tokens") or 0 for reply in replies)
        price = prices[slug]
        cost = (
            tokens_in * float(price["usd_per_million_input"])
            + tokens_out * float(price["usd_per_million_output"])
        ) / 1e6
        same = 0
        for patient in patients:
            outcomes = [
                outcome(run[patient]) if patient in run else "MISSING"
                for run in arm["runs"]
            ]
            same += len(set(outcomes)) == 1
            per_patient[patient].append(" | ".join(outcomes))
            modal[patient].append(Counter(outcomes).most_common(1)[0][0])
        arm_rows.append(
            [
                name,
                slug,
                price["quantization"],
                len(arm["runs"]),
                len(records),
                sum(outcome(r) != NO_ANSWER for r in records),
                same,
                len(replies),
                tokens_in,
                tokens_out,
                round(cost, 4),
                round(cost / len(records) * 50, 3) if records else "",
                "; ".join(sorted({str(r.get("provider")) for r in replies})),
            ]
        )

    write_csv(
        out / "arms.csv",
        [
            "arm",
            "provider",
            "quantization",
            "repeats",
            "patient_runs",
            "answered",
            "patients_same_answer_every_repeat",
            "model_calls",
            "input_tokens",
            "output_tokens",
            "cost_usd",
            "cost_usd_per_50_patients",
            "providers_that_answered",
        ],
        arm_rows,
    )
    names = list(arms)
    for patient in patients:
        per_patient[patient].append(len(set(modal[patient])) == 1)
        per_patient[patient].append(reference.get(patient, ""))
    write_csv(
        out / "per_patient.csv",
        [
            "patient",
            *names,
            "same_most_common_answer_in_every_arm",
            "cluster_20_repeats_old_contract",
        ],
        list(per_patient.values()),
    )
    agree = sum(len(set(modal[p])) == 1 for p in patients)
    write_csv(
        out / "summary.csv",
        ["measure", "value"],
        [
            ["patients", len(patients)],
            ["patients_whose_most_common_answer_matches_in_every_arm", agree],
        ],
    )
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (out / "README.md").write_text(
        "# OpenRouter provider comparison\n\n"
        f"Made by `experiments/openrouter_providers/compare_providers.py` from "
        f"{sum(len(a['reps']) for a in arms.values())} run folders; "
        "see `provenance.json` for the commits and the run folders.\n\n"
        "- `arms.csv`: one row per provider arm.\n"
        "- `per_patient.csv`: each arm's answer in every repeat, and the cluster's "
        "20-repeat tally (old task contract, a reference only).\n"
        "- `summary.csv`: patients whose most common answer is the same in every arm.\n"
        "- `prices.csv`: the prices `cost_usd` uses.\n\n"
        "Remake with the command in `experiments/openrouter_providers/README.md`, "
        "passing `--prices` this folder's `prices.csv`; the tables then match exactly.\n"
    )
    print(out)


if __name__ == "__main__":
    main()
