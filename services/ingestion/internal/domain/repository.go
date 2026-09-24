package domain

import "context"

// SourceRepository persists ingested documents, keyed by (DocumentID,
// content hash): re-ingesting unchanged content is a no-op, and a changed
// hash for the same DocumentID is a new version, never an overwrite.
type SourceRepository interface {
	// Exists reports whether a document with this exact DocumentID and
	// content hash has already been saved.
	Exists(ctx context.Context, documentID, hash string) (bool, error)
	Save(ctx context.Context, doc Document) error
}
