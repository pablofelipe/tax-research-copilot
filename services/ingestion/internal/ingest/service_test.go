package ingest

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/domain"
)

type fakeFetcher struct {
	body []byte
	err  error
}

func (f fakeFetcher) Fetch(ctx context.Context, url string) ([]byte, error) {
	return f.body, f.err
}

type fakeParser struct {
	parsed ParsedDocument
	err    error
}

func (f fakeParser) Parse(html []byte) (ParsedDocument, error) {
	return f.parsed, f.err
}

type fakeRepository struct {
	existing map[string]bool
	saved    []domain.Document
	saveErr  error
}

func (f *fakeRepository) Exists(ctx context.Context, documentID, hash string) (bool, error) {
	return f.existing[documentID+"|"+hash], nil
}

func (f *fakeRepository) Save(ctx context.Context, doc domain.Document) error {
	if f.saveErr != nil {
		return f.saveErr
	}
	f.saved = append(f.saved, doc)
	return nil
}

func aParsedDocument() ParsedDocument {
	return ParsedDocument{
		Title:       "LEI COMPLEMENTAR Nº 214, DE 16 DE JANEIRO DE 2025",
		PublishedAt: time.Date(2025, time.January, 16, 0, 0, 0, 0, time.UTC),
		FullText:    "texto da lei",
		SourceType:  domain.SourceTypePrimary,
	}
}

func TestIngestSavesANewDocument(t *testing.T) {
	repo := &fakeRepository{existing: map[string]bool{}}
	service := NewService(fakeFetcher{body: []byte("<html></html>")}, fakeParser{parsed: aParsedDocument()}, repo)

	err := service.Ingest(context.Background(), "https://example.org/lc214", "lc-214-2025")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(repo.saved) != 1 {
		t.Fatalf("expected 1 saved document, got %d", len(repo.saved))
	}
	saved := repo.saved[0]
	if saved.DocumentID != "lc-214-2025" || saved.Title != aParsedDocument().Title {
		t.Fatalf("saved document does not match parsed data: %+v", saved)
	}
}

func TestIngestIsANoOpWhenContentIsUnchanged(t *testing.T) {
	parsed := aParsedDocument()
	doc := domain.Document{
		DocumentID:  "lc-214-2025",
		SourceType:  parsed.SourceType,
		Title:       parsed.Title,
		PublishedAt: parsed.PublishedAt,
		FullText:    parsed.FullText,
		URL:         "https://example.org/lc214",
	}
	repo := &fakeRepository{existing: map[string]bool{"lc-214-2025|" + doc.Hash(): true}}
	service := NewService(fakeFetcher{body: []byte("<html></html>")}, fakeParser{parsed: parsed}, repo)

	err := service.Ingest(context.Background(), "https://example.org/lc214", "lc-214-2025")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(repo.saved) != 0 {
		t.Fatalf("expected no save for unchanged content, got %d", len(repo.saved))
	}
}

func TestIngestReturnsErrorWhenFetchFails(t *testing.T) {
	repo := &fakeRepository{existing: map[string]bool{}}
	service := NewService(fakeFetcher{err: errors.New("network down")}, fakeParser{parsed: aParsedDocument()}, repo)

	if err := service.Ingest(context.Background(), "https://example.org/lc214", "lc-214-2025"); err == nil {
		t.Fatal("expected an error when fetch fails, got nil")
	}
}

func TestIngestReturnsErrorWhenParseFails(t *testing.T) {
	repo := &fakeRepository{existing: map[string]bool{}}
	service := NewService(fakeFetcher{body: []byte("<html></html>")}, fakeParser{err: errors.New("bad markup")}, repo)

	if err := service.Ingest(context.Background(), "https://example.org/lc214", "lc-214-2025"); err == nil {
		t.Fatal("expected an error when parse fails, got nil")
	}
}
