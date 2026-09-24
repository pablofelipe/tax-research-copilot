from collections.abc import Callable
from datetime import datetime

from app.core.schemas import AuditedCitation, AuditRecord, OutOfScopeResponse, TaxResearchResponse


def build_audit_record(
    *,
    thread_id: str,
    query: str,
    response: TaxResearchResponse | OutOfScopeResponse,
    human_decision: str | None,
    clock: Callable[[], datetime],
) -> AuditRecord:
    if isinstance(response, OutOfScopeResponse):
        return AuditRecord(
            thread_id=thread_id,
            query=query,
            in_scope=False,
            human_decision=human_decision,
            recorded_at=clock(),
        )

    citations: dict[tuple[str, str], AuditedCitation] = {}
    for sub_answer in response.sub_answers:
        for citation in sub_answer.citations:
            key = (citation.document_id, citation.content_hash)
            citations[key] = AuditedCitation(
                document_id=citation.document_id,
                title=citation.title,
                content_hash=citation.content_hash,
            )

    return AuditRecord(
        thread_id=thread_id,
        query=query,
        in_scope=True,
        sub_questions=[sa.sub_question for sa in response.sub_answers],
        citations=list(citations.values()),
        disputed_topics=[dp.topic for dp in response.disputed_positions],
        overall_confidence=response.overall_confidence,
        requires_human_review=response.requires_human_review,
        human_decision=human_decision,
        recorded_at=clock(),
    )
