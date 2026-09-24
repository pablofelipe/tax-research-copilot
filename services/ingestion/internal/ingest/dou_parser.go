package ingest

import (
	"bytes"
	"fmt"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/domain"
)

// ParsedDocument is what a Parser extracts from a raw page — everything a
// specific source's markup can honestly tell it, including SourceType
// (which the parser decides by construction, e.g. every DOU page is
// primary). DocumentID and URL are the caller's responsibility.
type ParsedDocument struct {
	Title       string
	PublishedAt time.Time
	FullText    string
	SourceType  domain.SourceType
}

// DOUParser extracts the law's title, publication date, and full text from
// a Diário Oficial da União (in.gov.br) page. Every DOU publication is a
// primary source by construction, so SourceType is never inferred here.
type DOUParser struct{}

func (DOUParser) Parse(html []byte) (ParsedDocument, error) {
	doc, err := goquery.NewDocumentFromReader(bytes.NewReader(html))
	if err != nil {
		return ParsedDocument{}, fmt.Errorf("dou parser: failed to parse HTML: %w", err)
	}

	title := extractTitle(doc)
	if title == "" {
		return ParsedDocument{}, fmt.Errorf("dou parser: could not find a title")
	}

	dateText := strings.TrimSpace(doc.Find("span.publicado-dou-data").First().Text())
	publishedAt, err := time.Parse("02/01/2006", dateText)
	if err != nil {
		return ParsedDocument{}, fmt.Errorf("dou parser: could not parse published date %q: %w", dateText, err)
	}

	var paragraphs []string
	doc.Find("div.texto-dou p").Each(func(_ int, s *goquery.Selection) {
		text := strings.TrimSpace(s.Text())
		if text != "" {
			paragraphs = append(paragraphs, text)
		}
	})
	if len(paragraphs) == 0 {
		return ParsedDocument{}, fmt.Errorf("dou parser: no text found in .texto-dou")
	}

	return ParsedDocument{
		Title:       title,
		PublishedAt: publishedAt,
		FullText:    strings.Join(paragraphs, "\n\n"),
		SourceType:  domain.SourceTypePrimary,
	}, nil
}

func extractTitle(doc *goquery.Document) string {
	raw := strings.TrimSpace(doc.Find("title").First().Text())
	parts := strings.SplitN(raw, " - ", 2)
	return strings.TrimSpace(parts[0])
}
