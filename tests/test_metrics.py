"""Tests for the span and confidence metrics, using small hand-made spans.

Nothing here reads a report, a run folder or an annotation file.
"""

import pytest

from oncotrace_bench.metrics import (
    confidence_score,
    mean_confidence_score,
    score_spans,
    span_coverage,
    span_hit,
)

DOC = "doc-1"


def span(start: int, end: int, document: str = DOC) -> dict:
    """Return a span dict in the form OncoTrace writes."""
    return {"document": document, "start": start, "end": end}


def test_span_hit_is_true_when_spans_share_a_character() -> None:
    """Spans that share even one character count as a hit."""
    assert span_hit(span(10, 20), [span(19, 30)])


def test_span_hit_is_false_when_spans_only_touch() -> None:
    """Spans that only touch at an edge share nothing."""
    assert not span_hit(span(10, 20), [span(20, 30)])


def test_span_hit_is_false_for_another_document() -> None:
    """Spans in different documents never overlap."""
    assert not span_hit(span(10, 20), [span(10, 20, document="doc-2")])


def test_coverage_is_intersection_over_annotated_length() -> None:
    """Coverage is the shared length over the annotated span's length."""
    assert span_coverage(span(0, 10), [span(5, 50)]) == pytest.approx(0.5)


def test_coverage_counts_overlapping_predictions_once() -> None:
    """Quotes that overlap each other cover each character once."""
    predicted = [span(0, 6), span(4, 10)]
    assert span_coverage(span(0, 10), predicted) == pytest.approx(1.0)


def test_coverage_does_not_penalize_a_longer_quote() -> None:
    """A long quote around the annotation still covers it fully."""
    assert span_coverage(span(10, 20), [span(0, 1000)]) == pytest.approx(1.0)


def test_score_spans_averages_over_annotated_spans() -> None:
    """Each annotated span is scored on its own, then averaged."""
    gold = [span(0, 10), span(100, 110)]
    predicted = [span(0, 10)]
    result = score_spans(gold, predicted)
    assert result == {
        "n_gold": 2,
        "any_hit": True,
        "all_hit": False,
        "hit_rate": 0.5,
        "mean_coverage": 0.5,
    }


def test_score_spans_all_hit_needs_every_annotated_span() -> None:
    """The strict hit needs the model to overlap every annotated span."""
    gold = [span(0, 10), span(100, 110)]
    predicted = [span(0, 10), span(105, 108)]
    result = score_spans(gold, predicted)
    assert result is not None
    assert result["all_hit"]
    assert result["any_hit"]


def test_score_spans_misses_when_the_model_quoted_elsewhere() -> None:
    """A quote far from the annotation is no hit and covers nothing."""
    result = score_spans([span(0, 10)], [span(500, 600)])
    assert result is not None
    assert not result["any_hit"]
    assert result["mean_coverage"] == pytest.approx(0.0)


def test_score_spans_is_none_without_an_annotated_span() -> None:
    """With no annotated span there is nothing to score."""
    assert score_spans([], [span(0, 10)]) is None


def test_confidence_score_follows_the_proposed_order() -> None:
    """Scores run from a confident right answer to a confident wrong one."""
    assert (
        confidence_score("high", True)
        > confidence_score("low", True)
        > confidence_score("low", False)
        > confidence_score("high", False)
    )


def test_confidence_score_accepts_another_table() -> None:
    """A caller can pass its own score table."""
    table = {("high", True): 1.0}
    assert confidence_score("high", True, table) == pytest.approx(1.0)


def test_mean_confidence_score_averages_answers() -> None:
    """The mean is taken over the answers given."""
    answers = [("high", True), ("high", False)]
    assert mean_confidence_score(answers) == pytest.approx(0.0)


def test_mean_confidence_score_is_none_without_answers() -> None:
    """No answers means no mean."""
    assert mean_confidence_score([]) is None
