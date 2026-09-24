package ingest

import (
	"context"
	"fmt"

	"go.opentelemetry.io/otel"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/domain"
)

var tracer = otel.Tracer("tax_research_copilot.ingestion")

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
	raw, err := s.fetch(ctx, url)
	if err != nil {
		return fmt.Errorf("ingest: fetch failed: %w", err)
	}

	parsed, err := s.parse(ctx, raw)
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

	exists, err := s.exists(ctx, documentID, doc.Hash())
	if err != nil {
		return fmt.Errorf("ingest: checking existing document failed: %w", err)
	}
	if exists {
		return nil
	}

	if err := s.save(ctx, doc); err != nil {
		return fmt.Errorf("ingest: save failed: %w", err)
	}
	return nil
}

func (s *Service) fetch(ctx context.Context, url string) ([]byte, error) {
	ctx, span := tracer.Start(ctx, "fetch")
	defer span.End()
	return s.fetcher.Fetch(ctx, url)
}

func (s *Service) parse(ctx context.Context, raw []byte) (ParsedDocument, error) {
	_, span := tracer.Start(ctx, "parse")
	defer span.End()
	return s.parser.Parse(raw)
}

func (s *Service) exists(ctx context.Context, documentID, hash string) (bool, error) {
	ctx, span := tracer.Start(ctx, "exists")
	defer span.End()
	return s.repository.Exists(ctx, documentID, hash)
}

func (s *Service) save(ctx context.Context, doc domain.Document) error {
	ctx, span := tracer.Start(ctx, "save")
	defer span.End()
	return s.repository.Save(ctx, doc)
}
