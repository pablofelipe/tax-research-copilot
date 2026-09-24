CREATE TABLE IF NOT EXISTS source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('primary', 'secondary')),
    title TEXT NOT NULL,
    published_at DATE NOT NULL,
    content_hash TEXT NOT NULL,
    full_text TEXT NOT NULL,
    url TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, content_hash)
);
