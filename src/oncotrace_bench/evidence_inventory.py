"""Inventory the passages in a report that bear on myometrial invasion (issue 8).

The inventory itself is hand-curated: a person read each candidate report and
recorded every passage about invasion or depth as character offsets plus a
category and a short tag (see `curated_passages.jsonl` in the issue 8 analysis
folder). This module adds what can be computed from those offsets:

- which passages the human annotation and the run cited,
- how many passages a counterfactual edit would have to change,
- unrelated passages of similar length to use as removal controls,
- a simple score for ranking patients as edit candidates.

Nothing here returns report text, so the outputs can be shared as they are.
"""

import json
import re
from pathlib import Path

# A passage "implies" one of these when it settles which half was invaded.
DEPTH_VALUES = {"less_than_50", "fifty_or_greater"}
OPPOSITE = {"less_than_50": "fifty_or_greater", "fifty_or_greater": "less_than_50"}

# Preliminary readings that the final diagnosis can supersede.
PRELIMINARY = {"frozen_section", "intraoperative_consult"}

# Passages that do not need to change for a percent flip or a removal edit:
# context (thickness, LVI, adenomyosis, other organs) rather than invasion.
CONTEXT_ONLY = {
    "none",
    "lvi_distractor_outer",
    "adenomyosis_distractor",
    "other_organ_distractor",
}

# Negative statements about invasion ("not apparent grossly"). They imply no
# half, but they are still evidence about invasion, so a remove-all edit has
# to remove them too or the expected answer drifts toward not_identified.
NEGATIVE_STATES = {
    "invasion_not_apparent_grossly",
    "no_gross_invasion",
    "no_definite_invasion_second_lesion",
}

# Lines that may not be used as unrelated control text: anything about
# invasion or depth, and anything that names people, dates, or page furniture.
RELATED_WORDS = re.compile(
    r"invasi|invad|infiltrat|myometri|depth|thick|percent|%|half|third|fourth|"
    r"stage|\bpT|FIGO|AJCC|serosa|transmural|superficial|deep|wall|frozen|"
    r"adenomyo|carcinoma|tumor|diagnos|comment|addend|synoptic|\bmm\b",
    re.IGNORECASE,
)
IDENTIFYING_WORDS = re.compile(
    r"name|M\.D|\bDr\b|signed|page|=====|accession|patient|date|labeled|"
    r"received|copies|criteria|discrepan|review|initial|FDA|report|"
    r"\d{1,2}/\d{1,2}/\d{2,4}",
    re.IGNORECASE,
)


def load_curated(path: Path) -> list[dict]:
    """Return the hand-curated inventory, one dict per patient."""
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Return True if two half-open character ranges share a character."""
    return min(a_end, b_end) > max(a_start, b_start)


def annotation_spans(annotation: dict) -> list[tuple[str, dict]]:
    """Return (field name, span) for every span in a human annotation."""
    return [
        (field, span)
        for field, value in annotation["fields"].items()
        for span in value.get("spans", [])
    ]


def run_spans(answer: dict) -> list[tuple[str, dict]]:
    """Return (citation group, span) for every citation in a run answer."""
    groups = [
        "depth_evidence",
        "quantified_depth",
        "specimen_evidence",
        "counterevidence",
    ]
    return [(group, span) for group in groups for span in answer.get(group, [])]


def cited_by(passage: dict, spans: list[tuple[str, dict]]) -> list[str]:
    """Return the sorted names of fields or groups whose spans touch a passage."""
    names = {
        name
        for name, span in spans
        if overlaps(passage["start"], passage["end"], span["start"], span["end"])
    }
    return sorted(names)


def needs_flip_edit(passage: dict, reference_half: str) -> bool:
    """Return True if a percent flip has to rewrite this passage.

    That is every passage that implies the reference half, plus any stage
    whose meaning depends on an unstated edition, plus distances or labels
    that are only consistent with the reference half.
    """
    implies = passage["implies"]
    return (
        implies == reference_half
        or implies == "ambiguous_edition"
        or implies == "consistent_with_" + reference_half
    )


def needs_removal_edit(passage: dict) -> bool:
    """Return True if a remove-all-invasion-evidence edit has to delete it."""
    return (
        passage["implies"] not in CONTEXT_ONLY or passage["states"] in NEGATIVE_STATES
    )


def starts_cleanly(lines: list[str], index: int) -> bool:
    """Return True if line `index` begins a new sentence, bullet, or list item.

    Control passages must start and end on such boundaries, so that deleting
    them leaves whole sentences behind rather than half of a wrapped one.
    """
    if index == 0 or index >= len(lines):
        return True
    line, previous = lines[index].strip(), lines[index - 1].strip()
    return (
        previous.endswith((".", ":", ")"))
        or previous == "-"
        or line.startswith("-")
        or re.match(r"[A-Z]{1,3}\d*[\s.,:-]", line) is not None
    )


def line_blocks(text: str, max_lines: int = 6) -> list[tuple[int, int]]:
    """Return (start, end) ranges of 1 to `max_lines` whole lines of unrelated text.

    A block qualifies if every line is non-empty, no line mentions invasion,
    depth, or identifying details, and the block starts and ends on a sentence
    or list-item boundary.
    """
    lines = text.split("\n")
    starts, position = [], 0
    for line in lines:
        starts.append(position)
        position += len(line) + 1
    blocks = []
    for first in range(len(lines)):
        if not starts_cleanly(lines, first):
            continue
        for last in range(first, min(first + max_lines, len(lines))):
            block = lines[first : last + 1]
            if not all(
                line.strip()
                and not RELATED_WORDS.search(line)
                and not IDENTIFYING_WORDS.search(line)
                for line in block
            ):
                break
            if starts_cleanly(lines, last + 1):
                blocks.append((starts[first], starts[last] + len(lines[last])))
    return blocks


def choose_controls(text: str, passages: list[dict], targets: list[dict]) -> list[dict]:
    """Pick one unrelated block of similar length for each removal target.

    Blocks never overlap an inventoried passage or each other, and never come
    from the first 5% of the document (where headers and identifiers sit).
    """
    earliest = len(text) // 20
    candidates = [
        (start, end)
        for start, end in line_blocks(text)
        if start >= earliest
        and not any(overlaps(start, end, p["start"], p["end"]) for p in passages)
    ]
    chosen = []
    for target in sorted(targets, key=lambda p: p["end"] - p["start"], reverse=True):
        length = target["end"] - target["start"]
        free = [
            (start, end)
            for start, end in candidates
            if not any(overlaps(start, end, c["start"], c["end"]) for c in chosen)
        ]
        if not free:
            break
        start, end = min(free, key=lambda block: abs((block[1] - block[0]) - length))
        chosen.append({"start": start, "end": end, "matched_to_start": target["start"]})
    return sorted(chosen, key=lambda c: c["start"])


def stage_edition(passages: list[dict]) -> str:
    """Return the staging edition named by the stage passages, if any."""
    states = " ".join(p["states"] for p in passages if p["category"] == "stage")
    if not states:
        return "no_stage"
    if "AJCC6" in states:
        return "AJCC6_2002"
    if "AJCC7" in states or "AJCC2010" in states:
        return "AJCC7_2010"
    return "edition_not_named"


def unit_inventory(entry: dict, text: str, annotation: dict, answer: dict) -> dict:
    """Return the full text-free inventory for one patient."""
    reference = annotation["fields"]["myometrial_invasion_percent"]["value"]
    human = annotation_spans(annotation)
    model = run_spans(answer)
    passages = []
    for passage in entry["passages"]:
        if not 0 <= passage["start"] < passage["end"] <= len(text):
            raise ValueError(f"{entry['unit']}: passage out of range {passage}")
        passages.append(
            {
                **passage,
                "length": passage["end"] - passage["start"],
                "cited_by_annotation": cited_by(passage, human),
                "cited_by_run": cited_by(passage, model),
                "flip_edit": needs_flip_edit(passage, reference),
                "removal_edit": needs_removal_edit(passage),
            }
        )
    removal_targets = [p for p in passages if p["removal_edit"]]
    return {
        "unit": entry["unit"],
        "document": annotation_document(annotation, answer),
        "document_chars": len(text),
        "reference_percent": reference,
        "run_percent": answer.get("myometrial_invasion_percent"),
        "classification": entry["classification"],
        "conflicts": entry["conflicts"],
        "ocr_issues": entry["ocr_issues"],
        "stage_edition": stage_edition(passages),
        "flip": entry["flip"],
        "removal": entry["removal"],
        "passages": passages,
        "removal_controls": choose_controls(text, passages, removal_targets),
    }


def annotation_document(annotation: dict, answer: dict) -> str:
    """Return the document ID that the spans of this patient point into."""
    for _, span in annotation_spans(annotation) + run_spans(answer):
        return span["document"]
    return ""


def summary_row(inventory: dict) -> dict:
    """Return one CSV row of counts and edit-feasibility flags for a patient."""
    passages = inventory["passages"]
    reference = inventory["reference_percent"]
    depth = [p for p in passages if p["implies"] in DEPTH_VALUES]
    definitive = [p for p in depth if p["category"] not in PRELIMINARY]
    stage_depth = [
        p
        for p in passages
        if p["category"] == "stage"
        and (p["implies"] in DEPTH_VALUES or p["implies"] == "ambiguous_edition")
    ]
    non_stage_categories = sorted(
        {p["category"] for p in definitive if p["category"] != "stage"}
    )
    against = [
        p
        for p in passages
        if p["implies"] in (OPPOSITE[reference], "regional_" + OPPOSITE[reference])
    ]
    flip = [p for p in passages if p["flip_edit"]]
    removal = [p for p in passages if p["removal_edit"]]
    controls = inventory["removal_controls"]
    # Passages that could pull a reader toward the wrong half or toward
    # "full thickness" without being depth evidence.
    distractors = {p["implies"] for p in passages if "distractor" in p["implies"]}
    if any("full_thickness_section_label" in p["states"] for p in passages):
        distractors.add("full_thickness_section_label")
    distractors = sorted(distractors)
    return {
        "unit": inventory["unit"],
        "reference_percent": reference,
        "document_chars": inventory["document_chars"],
        "classification": inventory["classification"],
        "n_passages": len(passages),
        "n_depth_passages": len(depth),
        "n_definitive_depth": len(definitive),
        "n_preliminary_depth": len(depth) - len(definitive),
        "depth_categories": ";".join(sorted({p["category"] for p in depth})),
        "n_non_stage_definitive_categories": len(non_stage_categories),
        "stage_edition": inventory["stage_edition"],
        "n_stage_depth_passages": len(stage_depth),
        "stage_only_redundancy": len(non_stage_categories) == 1
        and len(stage_depth) > 0,
        "n_passages_against_reference": len(against),
        "n_ocr_issues": len(inventory["ocr_issues"]),
        "distractors": ";".join(distractors),
        "annotation_cited_depth": sum(bool(p["cited_by_annotation"]) for p in depth),
        "run_cited_depth": sum(bool(p["cited_by_run"]) for p in depth),
        "flip_passages": len(flip),
        "flip_passages_definitive": sum(p["category"] not in PRELIMINARY for p in flip),
        "flip_edits_hand": inventory["flip"]["edits_needed"],
        "flip_clean_hand": inventory["flip"]["clean"],
        "removal_passages": len(removal),
        "removal_chars": sum(p["length"] for p in removal),
        "removal_edits_hand": inventory["removal"]["edits_needed"],
        "removal_coherent_hand": inventory["removal"]["coherent"],
        "stage_remains_after_removal_hand": inventory["removal"]["stage_remains"],
        "n_controls": len(controls),
        "control_chars": sum(c["end"] - c["start"] for c in controls),
    }


def flip_score(row: dict) -> float:
    """Lower is better: few definitive passages to rewrite and nothing messy."""
    return (
        row["flip_passages_definitive"]
        + 2 * (row["classification"] == "conflicting")
        + (not row["flip_clean_hand"])
        + row["n_ocr_issues"]
        + row["document_chars"] / 10000
    )


def removal_score(row: dict) -> float:
    """Lower is better: few passages to delete and a coherent report left over."""
    return (
        row["removal_passages"]
        + 3 * (not row["removal_coherent_hand"])
        + 2 * (row["classification"] == "conflicting")
        + row["n_ocr_issues"]
        + row["document_chars"] / 10000
    )
