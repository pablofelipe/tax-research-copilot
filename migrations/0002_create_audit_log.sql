CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL,
    query TEXT NOT NULL,
    in_scope BOOLEAN NOT NULL,
    sub_questions JSONB NOT NULL DEFAULT '[]',
    citations JSONB NOT NULL DEFAULT '[]',
    disputed_topics JSONB NOT NULL DEFAULT '[]',
    overall_confidence DOUBLE PRECISION,
    requires_human_review BOOLEAN,
    human_decision TEXT,
    recorded_at TIMESTAMPTZ NOT NULL
);
