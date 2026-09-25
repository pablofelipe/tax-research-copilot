import argparse
import sys

import httpx
import psycopg

from app.adapters.ollama_embedding_client import OllamaEmbeddingClient
from app.adapters.pgvector_chunk_repository import PgVectorChunkRepository
from app.core.indexing import Indexer

DEFAULT_DATABASE_URL = "postgres://tax_research:tax_research@localhost:5432/tax_research"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Chunk, embed, and index a source_documents row into pgvector for retrieval."
    )
    parser.add_argument("document_id", help="the document_id to index, as written by the ingestion CLI")
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    args = parser.parse_args(argv)

    conn = psycopg.connect(args.database_url, autocommit=True)
    row = conn.execute(
        """
        SELECT document_id, source_type, title, published_at, content_hash, full_text, url
        FROM source_documents
        WHERE document_id = %s
        ORDER BY ingested_at DESC
        LIMIT 1
        """,
        (args.document_id,),
    ).fetchone()

    if row is None:
        parser.error(f"no source_documents row found for document_id={args.document_id!r}")

    document_id, source_type, title, published_at, content_hash, full_text, url = row

    embedding_http = httpx.Client(base_url=args.ollama_url, timeout=600.0)
    embedding = OllamaEmbeddingClient(model=EMBEDDING_MODEL, client=embedding_http)
    indexer = Indexer(embedding, PgVectorChunkRepository(conn))

    count = indexer.index_document(
        document_id=document_id,
        source_type=source_type,
        title=title,
        published_at=published_at,
        content_hash=content_hash,
        full_text=full_text,
        url=url,
    )
    print(f"indexed {count} chunks for {document_id!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
