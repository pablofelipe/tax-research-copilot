CREATE EXTENSION IF NOT EXISTS vector;

-- document_id is not FK'd to source_documents(document_id): that table's
-- only unique constraint is the composite (document_id, content_hash), so a
-- single-column FK isn't possible without altering the Go service's schema.
-- The two tables stay loosely coupled by convention instead.
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('primary', 'secondary')),
    title TEXT NOT NULL,
    published_at DATE NOT NULL,
    content_hash TEXT NOT NULL,
    url TEXT,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, content_hash, chunk_index)
);

CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
