import pytest

from app.core.schemas import DisputedPosition, SourceCitation, SubAnswer
from app.graph.evaluator import Evaluator, EvaluatorError


def _citation(**overrides) -> SourceCitation:
    defaults = dict(
        source_type="primary",
        document_id="lc-214-2025",
        title="LC 214/2025",
        published_at="2025-01-16",
        content_hash="abc123",
        excerpt="Fica instituida a Contribuicao sobre Bens e Servicos (CBS).",
        url=None,
    )
    defaults.update(overrides)
    return SourceCitation(**defaults)


def _sub_answer(confidence: float, **overrides) -> SubAnswer:
    defaults = dict(
        sub_question="Quando o CBS entra em vigor?",
        answer="A partir de 2026, de forma escalonada.",
        citations=[_citation()],
        confidence=confidence,
    )
    defaults.update(overrides)
    return SubAnswer(**defaults)


def test_evaluate_uses_the_weakest_subanswer_as_overall_confidence():
    evaluator = Evaluator()
    sub_answers = [_sub_answer(0.95), _sub_answer(0.6), _sub_answer(0.8)]

    result = evaluator.evaluate(sub_answers, disputed_positions=[])

    assert result.overall_confidence == 0.6


def test_evaluate_does_not_require_review_when_confidence_meets_threshold_and_no_disputes():
    evaluator = Evaluator()
    sub_answers = [_sub_answer(0.9)]

    result = evaluator.evaluate(sub_answers, disputed_positions=[])

    assert result.requires_human_review is False


def test_evaluate_requires_review_when_confidence_below_threshold():
    evaluator = Evaluator()
    sub_answers = [_sub_answer(0.5)]

    result = evaluator.evaluate(sub_answers, disputed_positions=[])

    assert result.requires_human_review is True


def test_evaluate_requires_review_when_disputes_exist_even_with_high_confidence():
    evaluator = Evaluator()
    sub_answers = [_sub_answer(0.9), _sub_answer(0.85)]
    disputed = [
        DisputedPosition(
            topic="vigencia do split payment",
            positions=[sub_answers[0], sub_answers[1]],
            resolution_note=None,
        )
    ]

    result = evaluator.evaluate(sub_answers, disputed_positions=disputed)

    assert result.requires_human_review is True


def test_evaluate_raises_when_sub_answers_is_empty():
    evaluator = Evaluator()

    with pytest.raises(EvaluatorError):
        evaluator.evaluate([], disputed_positions=[])


def test_evaluate_respects_a_custom_threshold():
    evaluator = Evaluator(threshold=0.95)
    sub_answers = [_sub_answer(0.9)]

    result = evaluator.evaluate(sub_answers, disputed_positions=[])

    assert result.requires_human_review is True
