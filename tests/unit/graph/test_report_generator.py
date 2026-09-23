from datetime import datetime, timezone

from app.core.schemas import DisputedPosition, SourceCitation, SubAnswer
from app.graph.evaluator import EvaluationResult
from app.graph.report_generator import ReportGenerator


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


def _sub_answer(confidence: float = 0.9, **overrides) -> SubAnswer:
    defaults = dict(
        sub_question="Quando o CBS entra em vigor?",
        answer="A partir de 2026, de forma escalonada.",
        citations=[_citation()],
        confidence=confidence,
    )
    defaults.update(overrides)
    return SubAnswer(**defaults)


FIXED_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _fixed_clock() -> datetime:
    return FIXED_NOW


def test_generate_returns_response_with_provided_fields():
    generator = ReportGenerator(clock=_fixed_clock)
    sub_answers = [_sub_answer()]
    evaluation = EvaluationResult(overall_confidence=0.9, requires_human_review=False)

    response = generator.generate(
        query="Quando o CBS entra em vigor?",
        sub_answers=sub_answers,
        disputed_positions=[],
        evaluation=evaluation,
    )

    assert response.query == "Quando o CBS entra em vigor?"
    assert response.sub_answers == sub_answers
    assert response.disputed_positions == []
    assert response.overall_confidence == 0.9
    assert response.requires_human_review is False


def test_generate_sets_generated_at_using_the_injected_clock():
    generator = ReportGenerator(clock=_fixed_clock)
    evaluation = EvaluationResult(overall_confidence=0.9, requires_human_review=False)

    response = generator.generate(
        query="Quando o CBS entra em vigor?",
        sub_answers=[_sub_answer()],
        disputed_positions=[],
        evaluation=evaluation,
    )

    assert response.generated_at == FIXED_NOW


def test_generate_leaves_human_review_notes_none_when_review_not_required():
    generator = ReportGenerator(clock=_fixed_clock)
    evaluation = EvaluationResult(overall_confidence=0.9, requires_human_review=False)

    response = generator.generate(
        query="Quando o CBS entra em vigor?",
        sub_answers=[_sub_answer()],
        disputed_positions=[],
        evaluation=evaluation,
    )

    assert response.human_review_notes is None


def test_generate_mentions_low_confidence_in_review_notes():
    generator = ReportGenerator(clock=_fixed_clock)
    evaluation = EvaluationResult(overall_confidence=0.5, requires_human_review=True)

    response = generator.generate(
        query="Quando o CBS entra em vigor?",
        sub_answers=[_sub_answer(confidence=0.5)],
        disputed_positions=[],
        evaluation=evaluation,
    )

    assert "0.50" in response.human_review_notes
    assert "confianca" in response.human_review_notes.lower()


def test_generate_mentions_disputed_topics_in_review_notes():
    generator = ReportGenerator(clock=_fixed_clock)
    sub_answers = [
        _sub_answer(answer="Vigora a partir de 2026."),
        _sub_answer(answer="Vigora a partir de 2027, segundo parecer de escritorio."),
    ]
    disputed = [
        DisputedPosition(
            topic="vigencia do split payment",
            positions=sub_answers,
            resolution_note=None,
        )
    ]
    evaluation = EvaluationResult(overall_confidence=0.9, requires_human_review=True)

    response = generator.generate(
        query="Quando o CBS entra em vigor?",
        sub_answers=sub_answers,
        disputed_positions=disputed,
        evaluation=evaluation,
    )

    assert "vigencia do split payment" in response.human_review_notes
