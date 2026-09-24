from datetime import date, datetime

from app.core.schemas import (
    AuditedCitation,
    DisputedPosition,
    OutOfScopeResponse,
    SourceCitation,
    SubAnswer,
    TaxResearchResponse,
)
from app.graph.audit import build_audit_record


def _clock() -> datetime:
    return datetime(2026, 1, 1)


def _citation(document_id: str = "lc-214-2025") -> SourceCitation:
    return SourceCitation(
        source_type="primary",
        document_id=document_id,
        title="LC 214/2025",
        published_at=date(2025, 1, 16),
        content_hash="abc123",
        excerpt="texto",
        url=None,
    )


def test_build_audit_record_for_a_completed_response():
    sub_answer = SubAnswer(
        sub_question="Quando o CBS entra em vigor?",
        answer="A partir de 2026.",
        citations=[_citation()],
        confidence=0.9,
    )
    response = TaxResearchResponse(
        query="Quando o CBS entra em vigor?",
        sub_answers=[sub_answer],
        disputed_positions=[],
        overall_confidence=0.9,
        requires_human_review=False,
        human_review_notes=None,
        generated_at=datetime(2026, 1, 1),
    )

    record = build_audit_record(
        thread_id="t1",
        query="Quando o CBS entra em vigor?",
        response=response,
        human_decision=None,
        clock=_clock,
    )

    assert record.thread_id == "t1"
    assert record.in_scope is True
    assert record.sub_questions == ["Quando o CBS entra em vigor?"]
    assert record.citations == [
        AuditedCitation(document_id="lc-214-2025", title="LC 214/2025", content_hash="abc123")
    ]
    assert record.overall_confidence == 0.9
    assert record.requires_human_review is False
    assert record.human_decision is None
    assert record.recorded_at == datetime(2026, 1, 1)


def test_build_audit_record_deduplicates_repeated_citations():
    sub_answer_1 = SubAnswer(
        sub_question="q1", answer="a1", citations=[_citation("doc-a")], confidence=0.9
    )
    sub_answer_2 = SubAnswer(
        sub_question="q2", answer="a2", citations=[_citation("doc-a")], confidence=0.9
    )
    response = TaxResearchResponse(
        query="pergunta",
        sub_answers=[sub_answer_1, sub_answer_2],
        disputed_positions=[],
        overall_confidence=0.9,
        requires_human_review=False,
        human_review_notes=None,
        generated_at=datetime(2026, 1, 1),
    )

    record = build_audit_record(
        thread_id="t2", query="pergunta", response=response, human_decision=None, clock=_clock
    )

    assert len(record.citations) == 1


def test_build_audit_record_includes_disputed_topics_and_human_decision():
    sub_answer_a = SubAnswer(
        sub_question="q1", answer="a1", citations=[_citation("doc-a")], confidence=0.5
    )
    sub_answer_b = SubAnswer(
        sub_question="q1", answer="a2", citations=[_citation("doc-b")], confidence=0.5
    )
    response = TaxResearchResponse(
        query="pergunta",
        sub_answers=[sub_answer_a, sub_answer_b],
        disputed_positions=[
            DisputedPosition(topic="vigencia", positions=[sub_answer_a, sub_answer_b])
        ],
        overall_confidence=0.5,
        requires_human_review=True,
        human_review_notes=None,
        generated_at=datetime(2026, 1, 1),
    )

    record = build_audit_record(
        thread_id="t3",
        query="pergunta",
        response=response,
        human_decision="approved",
        clock=_clock,
    )

    assert record.disputed_topics == ["vigencia"]
    assert record.human_decision == "approved"


def test_build_audit_record_for_an_out_of_scope_response():
    response = OutOfScopeResponse(
        query="Qual a capital da Franca?",
        message="fora do escopo",
        generated_at=datetime(2026, 1, 1),
    )

    record = build_audit_record(
        thread_id="t4",
        query="Qual a capital da Franca?",
        response=response,
        human_decision=None,
        clock=_clock,
    )

    assert record.in_scope is False
    assert record.sub_questions == []
    assert record.citations == []
    assert record.overall_confidence is None
    assert record.requires_human_review is None
