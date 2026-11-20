"""Span and confidence metrics for OncoTrace answers (issue #52).

Label metrics (accuracy, precision, recall) already come from
`oncotrace.score.summarize`; they are not repeated here. This module adds the
two metrics that are not there yet:

* span metrics: does a quote the model gave overlap the span a person
  annotated, and how much of the annotated span does it cover;
* a confidence score that rewards a confident correct answer and penalizes a
  confident wrong one.

Spans are dicts with "document", "start" and "end" (character offsets), the
form OncoTrace writes in `answer["quotes"]` and annotations hold in `spans`.
Overlap is measured with `records.overlap` and `records.covered_fraction`, so
there is one definition of overlap in the repo.

Only offsets, labels and scores come out of here. Report text is never read.
"""

from oncotrace_bench.records import covered_fraction, overlap

# Score for (the model's confidence, whether the label was correct). Helena Wu's proposal
# fixed the order (confident and right, unsure and right, unsure and wrong,
# confident and wrong) but gave no numbers. The numbers and the "medium" level,
# placed halfway between "high" and "low", are choices made here. Callers can
# pass their own table to change any value.
CONFIDENCE_SCORES: dict[tuple[str, bool], float] = {
    ("high", True): 2.0,
    ("medium", True): 1.5,
    ("low", True): 1.0,
    ("low", False): -1.0,
    ("medium", False): -1.5,
    ("high", False): -2.0,
}


def span_hit(gold: dict, predicted: list[dict]) -> bool:
    """Return True if any predicted span shares at least one character with `gold`."""
    return any(overlap(gold, span) > 0 for span in predicted)


def span_coverage(gold: dict, predicted: list[dict]) -> float:
    """Return the fraction of the annotated span `gold` that the predicted spans cover.

    This is intersection / length of the annotated span. Predicted spans that
    overlap each other are counted once. It does not penalize a predicted span
    for being longer than the annotation: a model that quotes the whole report
    covers every annotated span completely. Read it together with `span_hit`
    and the length of what was quoted.
    """
    return covered_fraction(gold, predicted)


def score_spans(gold_spans: list[dict], predicted: list[dict]) -> dict | None:
    """Score one answer's quotes against the spans a person annotated for it.

    Span scores are an approximation. The same fact can appear twice in a report,
    so a model that quotes the other copy scores as a miss, and an answer that
    needs two sentences together has no way to say so in the annotation. Treat a
    low score as a reason to look at the case, and read `any_hit` (lenient) next
    to `all_hit` (strict): the truth is between them.

    Args:
        gold_spans: The annotated spans for one field of one patient.
        predicted: The spans the model quoted for the same field.

    Returns:
        None when there is nothing to score (no annotated span, as when the
        annotated value is "none_stated"). Otherwise a dict with:
        `n_gold` (annotated spans), `any_hit` (the model overlapped at least one
        of them), `all_hit` (it overlapped every one), `hit_rate` (share of
        annotated spans it overlapped) and `mean_coverage` (average fraction of
        an annotated span it covered).
    """
    if not gold_spans:
        return None
    hits = [span_hit(gold, predicted) for gold in gold_spans]
    coverage = [span_coverage(gold, predicted) for gold in gold_spans]
    return {
        "n_gold": len(gold_spans),
        "any_hit": any(hits),
        "all_hit": all(hits),
        "hit_rate": sum(hits) / len(hits),
        "mean_coverage": sum(coverage) / len(coverage),
    }


def confidence_score(
    confidence: str,
    correct: bool,
    table: dict[tuple[str, bool], float] | None = None,
) -> float:
    """Return the reward or penalty for one answer.

    Args:
        confidence: "high", "medium" or "low", as the model reported it.
        correct: Whether the answer's label matched the reference.
        table: Scores to use instead of `CONFIDENCE_SCORES`.

    Raises:
        KeyError: If the table has no entry for this confidence and outcome.
    """
    return (table or CONFIDENCE_SCORES)[(confidence, correct)]


def mean_confidence_score(
    answers: list[tuple[str, bool]],
    table: dict[tuple[str, bool], float] | None = None,
) -> float | None:
    """Return the average confidence score over (confidence, correct) pairs.

    Units the model did not answer have no confidence; leave them out of
    `answers` and report how many were left out next to this number.
    """
    if not answers:
        return None
    scores = [confidence_score(conf, ok, table) for conf, ok in answers]
    return sum(scores) / len(scores)
