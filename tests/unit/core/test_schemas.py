from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.schemas import DisputedPosition, SourceCitation, SubAnswer, TaxResearchResponse


def _citation(**overrides) -> dict:
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
    return defaults


def _sub_answer(**overrides) -> SubAnswer:
    defaults = dict(
        sub_question="Quando o CBS entra em vigor?",
        answer="A partir de 2026, de forma escalonada.",
        citations=[SourceCitation(**_citation())],
        confidence=0.9,
    )
    defaults.update(overrides)
    return SubAnswer(**defaults)


def test_subanswer_rejects_empty_citations():
    with pytest.raises(ValidationError):
        SubAnswer(
            sub_question="Quando o CBS entra em vigor?",
            answer="A partir de 2026, de forma escalonada.",
            citations=[],
            confidence=0.9,
        )


def test_subanswer_accepts_at_least_one_citation():
    sub_answer = _sub_answer()

    assert sub_answer.citations[0].document_id == "lc-214-2025"


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_subanswer_rejects_confidence_outside_unit_interval(confidence):
    with pytest.raises(ValidationError):
        _sub_answer(confidence=confidence)


def test_disputed_position_rejects_a_single_position():
    with pytest.raises(ValidationError):
        DisputedPosition(
            topic="Momento de vigencia do split payment",
            positions=[_sub_answer()],
            resolution_note=None,
        )


def test_disputed_position_accepts_two_conflicting_positions():
    disputed = DisputedPosition(
        topic="Momento de vigencia do split payment",
        positions=[
            _sub_answer(answer="Vigora a partir de 2026."),
            _sub_answer(answer="Vigora a partir de 2027, segundo parecer de escritorio."),
        ],
        resolution_note="Receita Federal ainda nao publicou posicao definitiva.",
    )

    assert len(disputed.positions) == 2


def test_response_rejects_no_human_review_when_confidence_below_threshold():
    with pytest.raises(ValidationError):
        TaxResearchResponse(
            query="Quando o CBS entra em vigor?",
            sub_answers=[_sub_answer()],
            disputed_positions=[],
            overall_confidence=0.5,
            requires_human_review=False,
            human_review_notes=None,
            generated_at=datetime(2026, 1, 1),
        )


def test_response_allows_no_human_review_when_confidence_meets_threshold():
    response = TaxResearchResponse(
        query="Quando o CBS entra em vigor?",
        sub_answers=[_sub_answer()],
        disputed_positions=[],
        overall_confidence=0.9,
        requires_human_review=False,
        human_review_notes=None,
        generated_at=datetime(2026, 1, 1),
    )

    assert response.requires_human_review is False


def test_response_rejects_empty_sub_answers():
    with pytest.raises(ValidationError):
        TaxResearchResponse(
            query="Quando o CBS entra em vigor?",
            sub_answers=[],
            disputed_positions=[],
            overall_confidence=0.9,
            requires_human_review=False,
            human_review_notes=None,
            generated_at=datetime(2026, 1, 1),
        )
