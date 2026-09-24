import os
from datetime import date
from pathlib import Path

import psycopg
import pytest

from app.adapters.pgvector_chunk_repository import PgVectorChunkRepository
from app.core.schemas import ChunkToIndex

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgres://tax_research:tax_research@localhost:5432/tax_research"
)
MIGRATION_PATH = Path(__file__).parents[2] / "migrations" / "0001_create_document_chunks.sql"


@pytest.fixture
def conn():
    connection = psycopg.connect(DATABASE_URL, autocommit=True)
    connection.execute(MIGRATION_PATH.read_text())
    connection.execute("DELETE FROM document_chunks")
    yield connection
    connection.close()


def _chunk(**overrides) -> ChunkToIndex:
    defaults = dict(
        document_id="lc-214-2025",
        source_type="primary",
        title="LC 214/2025",
        published_at=date(2025, 1, 16),
        content_hash="abc123",
        url="https://example.org/lc214",
        chunk_index=0,
        chunk_text="texto do trecho",
        embedding=[0.1] * 768,
    )
    defaults.update(overrides)
    return ChunkToIndex(**defaults)


@pytest.mark.integration
def test_save_and_search_round_trip(conn):
    repository = PgVectorChunkRepository(conn)
    repository.save_chunks([_chunk()])

    results = repository.search(query_embedding=[0.1] * 768, top_k=5)

    assert len(results) == 1
    assert results[0].document_id == "lc-214-2025"
    assert results[0].chunk_text == "texto do trecho"
    assert results[0].content_hash == "abc123"


@pytest.mark.integration
def test_search_orders_by_similarity_closest_first(conn):
    repository = PgVectorChunkRepository(conn)
    close = _chunk(chunk_index=0, chunk_text="proximo", embedding=[0.9] + [0.0] * 767)
    far = _chunk(chunk_index=1, chunk_text="distante", embedding=[-0.9] + [0.0] * 767)
    repository.save_chunks([far, close])

    results = repository.search(query_embedding=[1.0] + [0.0] * 767, top_k=2)

    assert [r.chunk_text for r in results] == ["proximo", "distante"]


@pytest.mark.integration
def test_save_chunks_is_idempotent_for_the_same_document_and_hash(conn):
    repository = PgVectorChunkRepository(conn)
    chunk = _chunk()

    repository.save_chunks([chunk])
    repository.save_chunks([chunk])

    results = repository.search(query_embedding=[0.1] * 768, top_k=10)
    assert len(results) == 1
