//go:build integration

package storage

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/domain"
)

func testPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://tax_research:tax_research@localhost:5432/tax_research"
	}

	pool, err := pgxpool.New(context.Background(), dsn)
	if err != nil {
		t.Fatalf("failed to connect to postgres: %v", err)
	}

	migration, err := os.ReadFile("../../migrations/0001_create_source_documents.sql")
	if err != nil {
		t.Fatalf("failed to read migration: %v", err)
	}
	if _, err := pool.Exec(context.Background(), string(migration)); err != nil {
		t.Fatalf("failed to apply migration: %v", err)
	}

	t.Cleanup(func() {
		pool.Exec(context.Background(), "DELETE FROM source_documents WHERE document_id LIKE 'test-%'")
		pool.Close()
	})

	return pool
}

func TestSaveAndExistsRoundTrip(t *testing.T) {
	pool := testPool(t)
	repo := NewPostgresRepository(pool)
	ctx := context.Background()

	doc := domain.Document{
		DocumentID:  "test-doc-1",
		SourceType:  domain.SourceTypePrimary,
		Title:       "Documento de teste",
		PublishedAt: time.Date(2025, time.January, 16, 0, 0, 0, 0, time.UTC),
		FullText:    "texto de teste",
		URL:         "https://example.org/test",
	}

	exists, err := repo.Exists(ctx, doc.DocumentID, doc.Hash())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if exists {
		t.Fatal("expected document not to exist before saving")
	}

	if err := repo.Save(ctx, doc); err != nil {
		t.Fatalf("unexpected error saving: %v", err)
	}

	exists, err = repo.Exists(ctx, doc.DocumentID, doc.Hash())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !exists {
		t.Fatal("expected document to exist after saving")
	}
}

// Save itself is not idempotent — it relies on the table's UNIQUE
// (document_id, content_hash) constraint as a defense-in-depth safety net.
// The no-op-on-unchanged-content behavior lives in Service.Ingest, which
// checks Exists before ever calling Save.
func TestSaveTwiceWithSameContentIsRejectedByUniqueConstraint(t *testing.T) {
	pool := testPool(t)
	repo := NewPostgresRepository(pool)
	ctx := context.Background()

	doc := domain.Document{
		DocumentID:  "test-doc-2",
		SourceType:  domain.SourceTypePrimary,
		Title:       "Documento de teste 2",
		PublishedAt: time.Date(2025, time.January, 16, 0, 0, 0, 0, time.UTC),
		FullText:    "texto de teste 2",
		URL:         "https://example.org/test2",
	}

	if err := repo.Save(ctx, doc); err != nil {
		t.Fatalf("unexpected error on first save: %v", err)
	}

	if err := repo.Save(ctx, doc); err == nil {
		t.Fatal("expected an error saving the same document_id+hash twice, got nil")
	}
}
