import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from app.core.schemas import ChunkSearchResult, ChunkToIndex


class PgVectorChunkRepository:
    """ChunkRepository adapter backed by PostgreSQL + pgvector. The
    psycopg.Connection is injected so this adapter is only exercised by
    real integration tests, never unit tests — the write/search logic
    itself is exercised through Indexer's and PgVectorRetrievalAdapter's
    fake-backed unit tests.
    """

    def __init__(self, conn: psycopg.Connection):
        register_vector(conn)
        self._conn = conn

    def save_chunks(self, chunks: list[ChunkToIndex]) -> None:
        with self._conn.cursor() as cur:
            for chunk in chunks:
                cur.execute(
                    """
                    INSERT INTO document_chunks
                        (document_id, source_type, title, published_at,
                         content_hash, url, chunk_index, chunk_text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (document_id, content_hash, chunk_index) DO NOTHING
                    """,
                    (
                        chunk.document_id,
                        chunk.source_type,
                        chunk.title,
                        chunk.published_at,
                        chunk.content_hash,
                        chunk.url,
                        chunk.chunk_index,
                        chunk.chunk_text,
                        Vector(chunk.embedding),
                    ),
                )

    def search(self, query_embedding: list[float], top_k: int) -> list[ChunkSearchResult]:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT document_id, source_type, title, published_at,
                       content_hash, url, chunk_text
                FROM document_chunks
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (Vector(query_embedding), top_k),
            )
            rows = cur.fetchall()

        return [
            ChunkSearchResult(
                document_id=row[0],
                source_type=row[1],
                title=row[2],
                published_at=row[3],
                content_hash=row[4],
                url=row[5],
                chunk_text=row[6],
            )
            for row in rows
        ]
