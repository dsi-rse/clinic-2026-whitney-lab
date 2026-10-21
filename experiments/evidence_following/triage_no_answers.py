"""Triage OncoTrace no_answer patients and the refusals that shape answers.

Two questions:

1. Why does a patient end with `no_answer`? Each one is put in one class:
   (a) never found the evidence, (b) a submission loop the harness kept
   refusing, (c) ran out of model calls for another reason, (d) replies cut
   off at max_completion_tokens, (e) server error.
2. When the harness refuses a submit, does the model change its *answer*
   (label, percent, depth basis) or only its citations?

How the harness behaves (OncoTrace e901b3f) and why it matters here:

- Only an accepted submit is logged as a `submit` event. A refused submit
  leaves only a `recoverable_error` event, and the tool-call arguments are
  never logged. So the values the model *tried* to submit are read from the
  reasoning of the model call that sent the submit (the last
  "field: value" it wrote for each field). That is an estimate.
- The vLLM GLM tool parser hands every argument over as text and converts an
  array argument with `json.loads`. When that fails the argument stays a
  string, and OncoTrace then loops over the string one character at a time.
  The first character, "[" or "{", is checked as a quote and refused. A
  refused quote of one character therefore means "the argument was garbled",
  not "the model quoted badly" (dsi-rse/oncotrace#5).

Writes two text-free CSV files (IDs, counts, labels, numbers only):

- no_answer_triage.csv: one row per no_answer patient, with its class and
  the evidence for it.
- refusals_run.csv: one row per patient, with counts of each refusal
  signature and whether the label, percent, or depth basis changed between
  the first submit attempt and the accepted answer.

Then prints a short summary. Called by run_experiment.py.
"""

import re
from collections import Counter
from pathlib import Path

import pandas as pd

# Allowed values of the answer fields the model chooses (from the task yaml).
FIELD_VALUES = {
    "myometrial_invasion": (
        "not_applicable",
        "not_identified",
        "present",
        "cannot_be_determined",
    ),
    "myometrial_invasion_percent": (
        "less_than_50",
        "fifty_or_greater",
        "cannot_be_determined",
        "not_applicable",
    ),
    "depth_basis": (
        "explicit_fraction_or_percentage",
        "estimated_without_number",
        "descriptive_full_thickness",
        "descriptive_other",
        "none_stated",
    ),
    "specimen_type": (
        "hysterectomy",
        "biopsy_or_curettage_only",
        "other_or_not_stated",
    ),
}
STATED_FIELDS = ("myometrial_invasion", "myometrial_invasion_percent", "depth_basis")

# Refusal families. Signatures not listed here count as "other".
CITATION_SIGNATURES = (
    "citation_quote_not_found",
    "citation_quote_ambiguous",
    "citation_document_ambiguous",
    "citation_not_read",
    "citation_malformed",
)
CONTRACT_SIGNATURES = (
    "quantified_depth_not_classified",
    "quantified_basis_uncited",
    "evidence_citations_missing",
    "overlapping_citations",
    "depth_evidence_missing",
    "invasion_percent_unresolved",
    "depth_requires_hysterectomy",
)
# Refusals of a field value that is not one of the allowed values.
NOT_ALLOWED_SUFFIX = "_not_allowed"

# A refused quote this short (after stripping) is a garbled argument.
GARBLED_QUOTE_CHARS = 1
# How many of the last refusals decide what a loop "is".
LOOP_WINDOW = 10
# Share of the loop window one signature must hold to name the loop.
LOOP_SHARE = 0.5


def events_of(record: dict, kind: str) -> list[dict]:
    """Return the events of one kind, in order."""
    return [event for event in record["events"] if event["kind"] == kind]


def refusals(record: dict) -> list[dict]:
    """Return the recoverable_error events (harness refusals), in order."""
    return events_of(record, "recoverable_error")


def is_garbled_quote(event: dict) -> bool:
    """Return True if a refusal turned down a one-character quote like "["."""
    rejected = event.get("rejected_citation")
    if not rejected:
        return False
    return len(rejected["quote"].strip()) <= GARBLED_QUOTE_CHARS


def signature_family(signature: str) -> str:
    """Return "citation", "contract", "field_value" or "other" for a signature."""
    if signature in CITATION_SIGNATURES:
        return "citation"
    if signature in CONTRACT_SIGNATURES:
        return "contract"
    if signature.endswith(NOT_ALLOWED_SUFFIX):
        return "field_value"
    return "other"


def compact_sequence(signatures: list[str]) -> str:
    """Write a list of signatures as runs, e.g. "a x3 > b > a x2"."""
    parts = []
    previous = None
    count = 0
    for signature in [*signatures, None]:
        if signature == previous:
            count += 1
            continue
        if previous is not None:
            parts.append(previous if count == 1 else f"{previous} x{count}")
        previous = signature
        count = 1
    return " > ".join(parts)


def fraction_read(record: dict) -> float:
    """Return the fraction of the patient's report characters any read returned."""
    covered = set()
    for event in events_of(record, "read"):
        for window in event["result"]["windows"]:
            covered.update(range(window["start"], window["end"]))
    total = record["document_chars"]
    return round(len(covered) / total, 3) if total else 0.0


def value_pattern(field: str) -> re.Pattern:
    """Return a regex for a "field: value" (or "field = value") mention.

    A colon or equals sign is required. Without it, the model restating the
    task instructions ("... as fifty_or_greater with depth_basis
    descriptive_full_thickness") is read as a decision.
    """
    values = "|".join(FIELD_VALUES[field])
    # (?![a-z_]) stops "myometrial_invasion" matching "..._percent".
    return re.compile(
        re.escape(field)
        + r"(?![a-z_])[\"'`*]{0,2}\s{0,2}[:=]\s{0,2}[\"'`*]{0,2}("
        + values
        + ")"
    )


def stated_values(text: str) -> dict[str, str]:
    """Return the last value the model wrote for each answer field in `text`.

    Only the value names are returned.
    """
    found = {}
    for field in STATED_FIELDS:
        matches = value_pattern(field).findall(text)
        if matches:
            found[field] = matches[-1]
    return found


def calls_with_outcomes(record: dict) -> list[dict]:
    """Return one entry per model call, with what the harness did with it.

    Each entry has the model_response event plus the refusal signatures and
    accepted submits that followed it, up to the next model call.
    """
    calls = []
    for event in record["events"]:
        if event["kind"] == "model_response":
            calls.append(
                {"response": event, "refused": [], "garbled": 0, "accepted": False}
            )
        elif not calls:
            continue
        elif event["kind"] == "recoverable_error":
            calls[-1]["refused"].append(event["signature"])
            calls[-1]["garbled"] += is_garbled_quote(event)
        elif event["kind"] == "submit":
            calls[-1]["accepted"] = True
    return calls


def submit_attempts(record: dict) -> list[dict]:
    """Return the model calls that sent a submit, with the values each stated.

    Values come from that call's reasoning; a field the call did not mention
    keeps the value from the previous submit call (the model usually only
    restates what it changes).
    """
    attempts = []
    carried: dict[str, str] = {}
    for call in calls_with_outcomes(record):
        response = call["response"]
        if "submit" not in response["called_tools"]:
            continue
        text = response["reasoning_text"] + "\n" + response["assistant_text"]
        carried = {**carried, **stated_values(text)}
        attempts.append(
            {
                "model_call": response["model_call"],
                "n_submit_calls": response["called_tools"].count("submit"),
                "refused": call["refused"],
                "accepted": call["accepted"],
                "stated": dict(carried),
            }
        )
    return attempts


def trailing_loop(record: dict) -> tuple[int, int | None, int]:
    """Describe the run of calls at the end that all got the same refusals.

    Returns (number of calls, first model call of the run, number of
    distinct completion-token counts in the run). One distinct count means
    that, at temperature 0, the model sent the very same submit every time.
    """
    length = 0
    start = None
    last_key = None
    tokens = set()
    for call in reversed(calls_with_outcomes(record)):
        key = tuple(call["refused"])
        if not key or (last_key is not None and key != last_key):
            break
        last_key = key
        length += 1
        start = call["response"]["model_call"]
        tokens.add(call["response"]["completion_tokens"])
    return length, start, len(tokens)


def longest_refusal_run(record: dict, same_tokens: bool) -> int:
    """Return the longest run of consecutive calls that got the same refusals.

    With `same_tokens`, the calls must also have the same completion-token
    count, which at temperature 0 means an identical resubmission.
    """
    best = 0
    run = 0
    last_key = None
    for call in calls_with_outcomes(record):
        if not call["refused"]:
            run = 0
            last_key = None
            continue
        key = tuple(call["refused"])
        if same_tokens:
            key = (key, call["response"]["completion_tokens"])
        run = run + 1 if key == last_key else 1
        last_key = key
        best = max(best, run)
    return best


def loop_signature(record: dict) -> str:
    """Return the signature that dominates the last refusals, or "" if none does."""
    last = [event["signature"] for event in refusals(record)][-LOOP_WINDOW:]
    if not last:
        return ""
    signature, count = Counter(last).most_common(1)[0]
    return signature if count / len(last) >= LOOP_SHARE else ""


def classify_no_answer(record: dict) -> tuple[str, str, str, str]:
    """Return (class, subtype, confidence, reason) for one no_answer record.

    Decision order:
    - reason truncated_without_tool_call -> (d) truncation.
    - no read, or under half the report read, and no submit -> (a).
    - budget spent on a refusal loop -> (b), with a subtype:
      "argument_garbled" when the refused quotes are one character long or a
      field value the model stated as valid was refused (the harness never
      received what the model wrote), "citation" for real quotes that are
      not verbatim, "contract" for contract-rule refusals,
      "citations_missing" when every citation group arrived empty,
      "blank_list_entry" when a blank unresolved_conflicts entry is refused.
    - budget spent without a loop -> (c).
    """
    reason = record["answer"]["reason"]
    attempts = submit_attempts(record)
    if reason == "truncated_without_tool_call":
        before = "after refused submits" if attempts else "before any submit"
        return (
            "d",
            "truncation",
            "high",
            f"3 tool-less replies at the token cap, {before}",
        )
    if reason != "model_call_budget_exhausted":
        return ("e", reason, "low", "unexpected no_answer reason")
    if not attempts and fraction_read(record) < LOOP_SHARE:
        return (
            "a",
            "evidence_not_found",
            "medium",
            "read under half the report, never submitted",
        )
    signature = loop_signature(record)
    loop_length, loop_start, loop_tokens = trailing_loop(record)
    if not signature:
        return ("c", "no_loop", "medium", "budget spent without one repeating refusal")
    tail = refusals(record)[-LOOP_WINDOW:]
    garbled = sum(is_garbled_quote(event) for event in tail)
    loop_text = (
        f"{signature} loop: calls {loop_start}-{record['model_calls']} "
        f"({loop_length} calls, {loop_tokens} distinct token counts)"
    )
    if garbled >= len(tail) * LOOP_SHARE:
        return (
            "b",
            "argument_garbled",
            "high",
            f"{loop_text}; refused quotes are 1 char",
        )
    if signature.endswith(NOT_ALLOWED_SUFFIX):
        field = signature.removesuffix(NOT_ALLOWED_SUFFIX)
        stated = stated_field_value(record, field)
        if stated in FIELD_VALUES.get(field, ()):
            return (
                "b",
                "argument_garbled",
                "high",
                f"{loop_text}; reasoning states a valid {field}",
            )
        return ("b", "field_value", "medium", loop_text)
    if signature == "evidence_citations_missing":
        return (
            "b",
            "citations_missing",
            "medium",
            f"{loop_text}; all groups arrived empty",
        )
    if signature.startswith("empty_"):
        return (
            "b",
            "blank_list_entry",
            "medium",
            f"{loop_text}; blank list entry refused",
        )
    family = signature_family(signature)
    if family in ("citation", "contract"):
        return ("b", family, "high", loop_text)
    return ("b", "other", "medium", loop_text)


def stated_field_value(record: dict, field: str) -> str | None:
    """Return the last "field: value" the model wrote in any reasoning, or None.

    Used for fields outside STATED_FIELDS (such as specimen_type). Only the
    value name is returned.
    """
    pattern = value_pattern(field)
    value = None
    for response in events_of(record, "model_response"):
        matches = pattern.findall(response["reasoning_text"])
        if matches:
            value = matches[-1]
    return value


def reference_values(annotation: dict | None) -> dict[str, str]:
    """Return the annotated label, percent and depth basis ("" if not annotated)."""
    if annotation is None:
        return {
            "reference_label": "",
            "reference_percent": "",
            "reference_depth_basis": "",
        }
    fields = annotation["fields"]
    return {
        "reference_label": fields["myometrial_invasion"]["value"],
        "reference_percent": fields["myometrial_invasion_percent"]["value"],
        "reference_depth_basis": fields["depth_basis"]["value"],
    }


def no_answer_row(unit: str, record: dict, annotation: dict | None) -> dict:
    """Return one text-free triage row for a no_answer record."""
    responses = events_of(record, "model_response")
    attempts = submit_attempts(record)
    first = attempts[0]["stated"] if attempts else {}
    last_response = responses[-1]
    triage_class, subtype, confidence, why = classify_no_answer(record)
    loop_calls, loop_start, loop_tokens = trailing_loop(record)
    signatures = [event["signature"] for event in refusals(record)]
    return {
        "unit": unit,
        "reason": record["answer"]["reason"],
        "triage_class": triage_class,
        "triage_subtype": subtype,
        "confidence": confidence,
        "why": why,
        "model_calls": record["model_calls"],
        "n_reads": len(events_of(record, "read")),
        "n_searches": len(events_of(record, "search")),
        "fraction_read": fraction_read(record),
        "document_chars": record["document_chars"],
        "n_refusals": len(signatures),
        "n_garbled_quotes": sum(is_garbled_quote(event) for event in refusals(record)),
        "refusal_sequence": compact_sequence(signatures),
        "final_loop_calls": loop_calls,
        "final_loop_start_call": loop_start or "",
        "final_loop_distinct_tokens": loop_tokens,
        "submit_attempted": bool(attempts),
        "n_submit_calls": sum(attempt["n_submit_calls"] for attempt in attempts),
        "attempted_label": first.get("myometrial_invasion", ""),
        "attempted_percent": first.get("myometrial_invasion_percent", ""),
        "attempted_depth_basis": first.get("depth_basis", ""),
        "n_truncated_calls": sum(r["finish_reason"] == "length" for r in responses),
        "n_nudges": len(events_of(record, "completion_nudge")),
        "last_finish_reason": last_response["finish_reason"],
        "last_completion_tokens": last_response["completion_tokens"],
        "peak_prompt_tokens": max(r["prompt_tokens"] or 0 for r in responses),
        "annotated": annotation is not None,
        **reference_values(annotation),
    }


def refusal_row(unit: str, record: dict, annotation: dict | None) -> dict:
    """Return one text-free row of refusal counts and answer changes for a record.

    `*_changed` compares the values stated for the first submit attempt with
    the accepted answer. It is blank when the patient has no accepted answer
    or the first attempt's reasoning did not state that field.
    """
    answer = record["answer"]
    answered = answer["status"] == "answered"
    attempts = submit_attempts(record)
    first = attempts[0] if attempts else None
    signatures = [event["signature"] for event in refusals(record)]
    families = Counter(signature_family(signature) for signature in signatures)
    row = {
        "unit": unit,
        "status": answer["status"],
        "reason": answer.get("reason", ""),
        "annotated": annotation is not None,
        "document_chars": record["document_chars"],
        "model_calls": record["model_calls"],
        "n_submit_calls": sum(attempt["n_submit_calls"] for attempt in attempts),
        "n_refused_submit_calls": sum(
            event["tool"] == "submit" for event in refusals(record)
        ),
        "first_submit_accepted": bool(first and first["accepted"]),
        "n_refusals": len(signatures),
        "n_citation_refusals": families["citation"],
        "n_contract_refusals": families["contract"],
        "n_field_value_refusals": families["field_value"],
        "n_other_refusals": families["other"],
        "n_garbled_quotes": sum(is_garbled_quote(event) for event in refusals(record)),
        "longest_same_refusal_run": longest_refusal_run(record, same_tokens=False),
        "longest_identical_run": longest_refusal_run(record, same_tokens=True),
        "final_quantified_depth_n": len(answer.get("quantified_depth", [])),
    }
    for field in STATED_FIELDS:
        stated = first["stated"].get(field, "") if first else ""
        final = answer.get(field, "") if answered else ""
        row[f"first_{field}"] = stated
        row[f"final_{field}"] = final
        row[f"{field}_changed"] = (stated != final) if (stated and final) else ""
    row.update(reference_values(annotation))
    for signature, count in sorted(Counter(signatures).items()):
        row[f"n_{signature}"] = count
    return row


# Report-length bins (characters) for the no_answer-rate table.
LENGTH_BINS = [0, 5000, 8000, 12000, 100000]


def print_triage(triage: pd.DataFrame) -> None:
    """Print the no_answer classes and one line per patient."""
    print(f"\n== no_answer triage ({len(triage)} patients) ==")
    print(triage.groupby(["triage_class", "triage_subtype"]).size().to_string())
    columns = [
        "unit",
        "triage_class",
        "triage_subtype",
        "confidence",
        "annotated",
        "why",
    ]
    print(triage[columns].to_string(index=False))


def print_changes(refusals: pd.DataFrame) -> None:
    """Print whether refused-then-accepted patients changed their answer."""
    answered = refusals[refusals["status"] == "answered"]
    refused_first = answered[~answered["first_submit_accepted"]]
    print(
        f"\n== answer changes: {len(refused_first)} answered patients had their "
        "first submit refused =="
    )
    for field in STATED_FIELDS:
        known = refused_first[refused_first[f"{field}_changed"] != ""]
        changed = known[known[f"{field}_changed"].astype(bool)]
        print(
            f"{field}: changed in {len(changed)} of {len(known)} with a stated "
            f"first value ({', '.join(changed['unit']) or 'none'})"
        )
    accepted_first = answered[answered["first_submit_accepted"]]
    for field in STATED_FIELDS:
        known = accepted_first[accepted_first[f"{field}_changed"] != ""]
        mismatched = known[known[f"{field}_changed"].astype(bool)]
        print(
            f"  check, first submit accepted: stated {field} differs from the "
            f"answer in {len(mismatched)} of {len(known)} (extraction error rate)"
        )


def print_quantified(refusals: pd.DataFrame) -> None:
    """Print how quantified_depth_not_classified refusals were resolved."""
    answered = refusals[refusals["status"] == "answered"].copy()
    column = "n_quantified_depth_not_classified"
    answered["hit_qdnc"] = answered.get(column, pd.Series(0, index=answered.index)) > 0
    print("\n== quantified_depth_not_classified (qdnc) ==")
    print(
        f"patients refused at least once: {int((refusals.get(column, 0) > 0).sum())} "
        f"of {len(refusals)}"
    )
    table = answered.groupby("hit_qdnc").agg(
        patients=("unit", "size"),
        final_quantified_empty=(
            "final_quantified_depth_n",
            lambda n: int((n == 0).sum()),
        ),
        final_explicit_basis=(
            "final_depth_basis",
            lambda b: int((b == "explicit_fraction_or_percentage").sum()),
        ),
    )
    print(table.to_string())


def print_annotated_gap(refusals: pd.DataFrame) -> None:
    """Print no_answer rates for annotated vs other patients by site and length."""
    table = refusals.copy()
    table["no_answer"] = table["status"] == "no_answer"
    table["site"] = table["unit"].str.split("-").str[1]
    table["length_bin"] = pd.cut(table["document_chars"], LENGTH_BINS)
    print("\n== annotated vs other patients ==")
    print(
        table.groupby("annotated")
        .agg(
            patients=("unit", "size"),
            no_answer=("no_answer", "sum"),
            median_chars=("document_chars", "median"),
            median_calls=("model_calls", "median"),
        )
        .to_string()
    )
    print("\nno_answer by report length:")
    print(
        table.groupby(["length_bin", "annotated"], observed=True)["no_answer"]
        .agg(["size", "sum"])
        .to_string()
    )
    print("\nno_answer by tissue source site (first ID block):")
    by_site = table.groupby("site")["no_answer"].agg(["size", "sum"])
    print(by_site.sort_values("size", ascending=False).head(10).to_string())


def write_tables(
    run: dict[str, dict], annotations: dict[str, dict], out_dir: Path
) -> None:
    """Build the two triage tables, save them in `out_dir`, and print a summary."""
    triage = pd.DataFrame(
        [
            no_answer_row(unit, record, annotations.get(unit))
            for unit, record in run.items()
            if record["answer"]["status"] == "no_answer"
        ]
    )
    refusals = pd.DataFrame(
        [
            refusal_row(unit, record, annotations.get(unit))
            for unit, record in run.items()
        ]
    )
    # Signature count columns are missing where a patient never got that refusal.
    count_columns = [c for c in refusals.columns if c.startswith("n_")]
    refusals[count_columns] = refusals[count_columns].fillna(0).astype(int)

    triage.to_csv(out_dir / "no_answer_triage.csv", index=False)
    refusals.to_csv(out_dir / "refusals_run.csv", index=False)
    print(f"wrote {len(triage)} rows to {out_dir / 'no_answer_triage.csv'}")
    print(f"wrote {len(refusals)} rows to {out_dir / 'refusals_run.csv'}")

    print_triage(triage)
    print_changes(refusals)
    print_quantified(refusals)
    print_annotated_gap(refusals)
