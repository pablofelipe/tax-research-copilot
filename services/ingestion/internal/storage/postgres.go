package storage

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/domain"
)

// PostgresRepository implements domain.SourceRepository against the
// source_documents table (see migrations/0001_create_source_documents.sql).
type PostgresRepository struct {
	pool *pgxpool.Pool
}

func NewPostgresRepository(pool *pgxpool.Pool) *PostgresRepository {
	return &PostgresRepository{pool: pool}
}

func (r *PostgresRepository) Exists(ctx context.Context, documentID, hash string) (bool, error) {
	var exists bool
	err := r.pool.QueryRow(
		ctx,
		"SELECT EXISTS (SELECT 1 FROM source_documents WHERE document_id = $1 AND content_hash = $2)",
		documentID, hash,
	).Scan(&exists)
	if err != nil {
		return false, fmt.Errorf("postgres repository: exists query failed: %w", err)
	}
	return exists, nil
}

func (r *PostgresRepository) Save(ctx context.Context, doc domain.Document) error {
	_, err := r.pool.Exec(
		ctx,
		`INSERT INTO source_documents
			(document_id, source_type, title, published_at, content_hash, full_text, url)
		 VALUES ($1, $2, $3, $4, $5, $6, $7)`,
		doc.DocumentID, string(doc.SourceType), doc.Title, doc.PublishedAt, doc.Hash(), doc.FullText, doc.URL,
	)
	if err != nil {
		return fmt.Errorf("postgres repository: insert failed: %w", err)
	}
	return nil
}
