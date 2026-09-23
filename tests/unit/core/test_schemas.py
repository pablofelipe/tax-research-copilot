import pytest
from pydantic import ValidationError

from app.core.schemas import SourceCitation, SubAnswer


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


def test_subanswer_rejects_empty_citations():
    with pytest.raises(ValidationError):
        SubAnswer(
            sub_question="Quando o CBS entra em vigor?",
            answer="A partir de 2026, de forma escalonada.",
            citations=[],
            confidence=0.9,
        )


def test_subanswer_accepts_at_least_one_citation():
    sub_answer = SubAnswer(
        sub_question="Quando o CBS entra em vigor?",
        answer="A partir de 2026, de forma escalonada.",
        citations=[SourceCitation(**_citation())],
        confidence=0.9,
    )

    assert sub_answer.citations[0].document_id == "lc-214-2025"
