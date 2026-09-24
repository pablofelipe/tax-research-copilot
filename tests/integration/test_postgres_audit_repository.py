import os
from datetime import datetime
from pathlib import Path

import psycopg
import pytest

from app.adapters.postgres_audit_repository import PostgresAuditRepository
from app.core.schemas import AuditedCitation, AuditRecord

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgres://tax_research:tax_research@localhost:5432/tax_research"
)
MIGRATION_PATH = Path(__file__).parents[2] / "migrations" / "0002_create_audit_log.sql"


@pytest.fixture
def conn():
    connection = psycopg.connect(DATABASE_URL, autocommit=True)
    connection.execute(MIGRATION_PATH.read_text())
    connection.execute("DELETE FROM audit_log")
    yield connection
    connection.close()


def _record(**overrides) -> AuditRecord:
    defaults = dict(
        thread_id="t1",
        query="Quando o CBS entra em vigor?",
        in_scope=True,
        sub_questions=["Quando o CBS entra em vigor?"],
        citations=[
            AuditedCitation(document_id="lc-214-2025", title="LC 214/2025", content_hash="abc123")
        ],
        disputed_topics=[],
        overall_confidence=0.9,
        requires_human_review=False,
        human_decision=None,
        recorded_at=datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return AuditRecord(**defaults)


@pytest.mark.integration
def test_record_persists_a_full_row(conn):
    repository = PostgresAuditRepository(conn)

    repository.record(_record())

    row = conn.execute(
        "SELECT thread_id, query, in_scope, sub_questions, citations, "
        "overall_confidence, requires_human_review, human_decision "
        "FROM audit_log WHERE thread_id = 't1'"
    ).fetchone()

    assert row[0] == "t1"
    assert row[1] == "Quando o CBS entra em vigor?"
    assert row[2] is True
    assert row[3] == ["Quando o CBS entra em vigor?"]
    assert row[4] == [{"document_id": "lc-214-2025", "title": "LC 214/2025", "content_hash": "abc123"}]
    assert row[5] == 0.9
    assert row[6] is False
    assert row[7] is None


@pytest.mark.integration
def test_record_persists_an_out_of_scope_row_with_null_confidence(conn):
    repository = PostgresAuditRepository(conn)

    repository.record(
        _record(
            thread_id="t2",
            in_scope=False,
            sub_questions=[],
            citations=[],
            overall_confidence=None,
            requires_human_review=None,
        )
    )

    row = conn.execute(
        "SELECT in_scope, overall_confidence, requires_human_review FROM audit_log WHERE thread_id = 't2'"
    ).fetchone()

    assert row[0] is False
    assert row[1] is None
    assert row[2] is None


@pytest.mark.integration
def test_record_persists_the_human_decision(conn):
    repository = PostgresAuditRepository(conn)

    repository.record(_record(thread_id="t3", human_decision="approved"))

    row = conn.execute(
        "SELECT human_decision FROM audit_log WHERE thread_id = 't3'"
    ).fetchone()

    assert row[0] == "approved"
