package ingest

import (
	"context"
	"fmt"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/domain"
)

// Parser extracts a ParsedDocument from a source's raw page bytes.
type Parser interface {
	Parse(html []byte) (ParsedDocument, error)
}

// Service orchestrates fetch -> parse -> hash -> compare -> save. Saving is
// skipped when a document with the same DocumentID and content hash
// already exists — re-ingesting unchanged content is a no-op, not an error.
type Service struct {
	fetcher    Fetcher
	parser     Parser
	repository domain.SourceRepository
}

func NewService(fetcher Fetcher, parser Parser, repository domain.SourceRepository) *Service {
	return &Service{fetcher: fetcher, parser: parser, repository: repository}
}

func (s *Service) Ingest(ctx context.Context, url, documentID string) error {
	raw, err := s.fetcher.Fetch(ctx, url)
	if err != nil {
		return fmt.Errorf("ingest: fetch failed: %w", err)
	}

	parsed, err := s.parser.Parse(raw)
	if err != nil {
		return fmt.Errorf("ingest: parse failed: %w", err)
	}

	doc := domain.Document{
		DocumentID:  documentID,
		SourceType:  parsed.SourceType,
		Title:       parsed.Title,
		PublishedAt: parsed.PublishedAt,
		FullText:    parsed.FullText,
		URL:         url,
	}

	exists, err := s.repository.Exists(ctx, documentID, doc.Hash())
	if err != nil {
		return fmt.Errorf("ingest: checking existing document failed: %w", err)
	}
	if exists {
		return nil
	}

	if err := s.repository.Save(ctx, doc); err != nil {
		return fmt.Errorf("ingest: save failed: %w", err)
	}
	return nil
}
