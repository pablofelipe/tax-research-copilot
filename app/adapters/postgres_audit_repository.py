import psycopg
from psycopg.types.json import Json

from app.core.schemas import AuditRecord


class PostgresAuditRepository:
    """AuditRepository adapter backed by PostgreSQL. Only exercised by
    real integration tests — the record-building logic itself is
    exercised through build_audit_record's fake-backed unit tests.
    """

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def record(self, entry: AuditRecord) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log
                    (thread_id, query, in_scope, sub_questions, citations,
                     disputed_topics, overall_confidence, requires_human_review,
                     human_decision, recorded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entry.thread_id,
                    entry.query,
                    entry.in_scope,
                    Json(entry.sub_questions),
                    Json([c.model_dump() for c in entry.citations]),
                    Json(entry.disputed_topics),
                    entry.overall_confidence,
                    entry.requires_human_review,
                    entry.human_decision,
                    entry.recorded_at,
                ),
            )
