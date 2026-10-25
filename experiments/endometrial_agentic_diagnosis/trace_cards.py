"""Write a one-card-per-patient summary of what OncoTrace did, with no report text.

Each card lists, step by step, what the model replied (tokens, whether it was cut off,
which tool it called), what it read, and what the checks refused, with repeats collapsed
("x19"). Patients are picked to cover each way a run ends, or given with --patients. The
cards say what happened; why it happened and what it means is for the person writing the
case study to add.

Example:
    python experiments/endometrial_agentic_diagnosis/trace_cards.py \
        --run agentic=/path/to/run --label issue9
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
LABEL_KEY = "myometrial_invasion"
DEPTH_KEY = "myometrial_invasion_percent"
SUBSTANTIVE_TOKENS = 200
LOOP_REFUSALS = 10  # a patient with this many refusals of one kind counts as stuck
CUT_OFF_REPLIES = 3  # a patient cut off this many times in a row never submitted
MIN_CARDS = 10  # the issue asks for at least ten documented traces
RECOVERED_REFUSALS = 5  # answered despite at least this many refusals


def load(folder: Path) -> dict[str, dict[str, Any]]:
    """Every finished unit record of one run, by patient."""
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((folder / "units").glob("*.json"))
    }


def steps(record: dict[str, Any]) -> list[str]:
    """The record as short step labels, in order."""
    out = []
    for event in record["events"]:
        kind = event["kind"]
        if kind == "model_response":
            tokens = event.get("completion_tokens") or 0
            cut = (
                " CUT OFF at the token cap"
                if event.get("finish_reason") == "length"
                else ""
            )
            tools = ",".join(
                t if isinstance(t, str) else t.get("name", "?")
                for t in event.get("called_tools") or []
            )
            out.append(
                f"reply {tokens} tokens{cut}" + (f" -> {tools}" if tools else "")
            )
        elif kind == "read":
            spans = [
                f"{w['start']}-{w['end']} of {w['document_chars']}"
                for w in event["result"]["windows"]
            ]
            out.append("read " + "; ".join(spans))
        elif kind == "search":
            out.append(f"search x{len(event['result'].get('searches', []))}")
        elif kind == "recoverable_error":
            out.append(f"REFUSED: {event['signature']}")
        elif kind == "submit":
            out.append("SUBMIT accepted")
        elif kind == "no_answer":
            out.append(f"NO ANSWER: {event.get('reason', '')}")
        elif kind == "completion_nudge":
            out.append("nudge to finish")
    return out


def collapse(labels: list[str]) -> list[str]:
    """Join runs of the identical step into one line with a count."""
    lines: list[str] = []
    for label in labels:
        if (
            lines
            and lines[-1].split(" x")[0] == label.split(" x")[0]
            and not label.startswith("search")
        ):
            count = (
                int(lines[-1].rsplit(" x", 1)[1]) + 1
                if " x" in lines[-1] and lines[-1].rsplit(" x", 1)[1].isdigit()
                else 2
            )
            lines[-1] = f"{label} x{count}"
        else:
            lines.append(label)
    return lines


def ending(record: dict[str, Any]) -> str:
    """How the patient ended."""
    answer = record.get("answer")
    if isinstance(answer, dict) and LABEL_KEY in answer:
        return f"answered {answer[LABEL_KEY]} / {answer.get(DEPTH_KEY)}"
    return "no answer: " + next(
        (e.get("reason", "") for e in record["events"] if e["kind"] == "no_answer"), ""
    )


def pick(records: dict[str, dict[str, Any]]) -> list[str]:
    """One or more patients for each way a run ends, chosen by fixed rules."""

    def stats(record: dict[str, Any]) -> dict[str, Any]:
        events = record["events"]
        signatures = [
            e["signature"] for e in events if e["kind"] == "recoverable_error"
        ]
        cut = sum(
            e.get("finish_reason") == "length"
            for e in events
            if e["kind"] == "model_response"
        )
        return {
            "answered": ending(record).startswith("answered"),
            "refusals": len(signatures),
            "top": Counter(signatures).most_common(1)[0][0] if signatures else "",
            "cut": cut,
        }

    info = {u: stats(r) for u, r in records.items()}
    chosen: list[str] = []
    cut_off = sorted(
        (
            u
            for u, i in info.items()
            if not i["answered"] and i["cut"] >= CUT_OFF_REPLIES
        ),
        key=lambda u: u,
    )
    chosen += cut_off[:3]
    for signature in (
        "citation_quote_not_found",
        "evidence_citations_missing",
        "quantified_depth_not_classified",
    ):
        group = sorted(
            u
            for u, i in info.items()
            if not i["answered"]
            and i["top"] == signature
            and i["refusals"] >= LOOP_REFUSALS
        )
        chosen += [u for u in group if u not in chosen][:1]
    recovered = sorted(
        (
            u
            for u, i in info.items()
            if i["answered"] and i["refusals"] >= RECOVERED_REFUSALS
        ),
        key=lambda u: -info[u]["refusals"],
    )
    chosen += recovered[:2]
    clean = sorted(
        u
        for u, i in info.items()
        if i["answered"] and i["refusals"] == 0 and i["cut"] == 0
    )
    chosen += clean[:1]
    for unit in sorted(
        (u for u, i in info.items() if not i["answered"]),
        key=lambda u: -info[u]["refusals"],
    ):
        if len(chosen) >= MIN_CARDS:
            break
        if unit not in chosen:
            chosen.append(unit)
    return chosen


def main() -> None:
    """Write the cards."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", required=True, metavar="NAME=FOLDER")
    parser.add_argument(
        "--patients",
        nargs="*",
        help="patients to write cards for; default: picked by rule",
    )
    parser.add_argument("--label", required=True, help="name for this result folder")
    parser.add_argument("--results-dir", type=Path, default=EXPERIMENT_DIR / "results")
    arguments = parser.parse_args()
    out = arguments.results_dir / arguments.label
    if out.exists():
        parser.error(
            f"{out} already exists; pick a new --label so earlier results are kept"
        )
    name, _, folder = arguments.run.partition("=")
    records = load(Path(folder))
    chosen = arguments.patients or pick(records)
    out.mkdir(parents=True)
    cards = [f"# Trace cards: {name} ({len(chosen)} patients)\n"]
    for unit in chosen:
        record = records[unit]
        cards.append(f"## {unit}: {ending(record)}\n")
        cards.append(
            f"{record['model_calls']} model calls, report {record['document_chars']} characters.\n"
        )
        cards += [f"{i}. {line}" for i, line in enumerate(collapse(steps(record)), 1)]
        cards.append(
            "\n**What happened:** _(write it)_  \n**Why:** _(write it)_  \n**So what:** _(write it)_\n"
        )
    (out / "trace_cards.md").write_text("\n".join(cards) + "\n", encoding="utf-8")
    print(f"wrote {out / 'trace_cards.md'}")
    print(", ".join(chosen))


if __name__ == "__main__":
    main()
