package ingest

import (
	"os"
	"strings"
	"testing"
	"time"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/domain"
)

func realFixture(t *testing.T) []byte {
	t.Helper()
	data, err := os.ReadFile("../../testdata/dou_lc214.html")
	if err != nil {
		t.Fatalf("failed to read fixture: %v", err)
	}
	return data
}

func TestParseExtractsTitleFromRealFixture(t *testing.T) {
	parsed, err := DOUParser{}.Parse(realFixture(t))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	want := "LEI COMPLEMENTAR Nº 214, DE 16 DE JANEIRO DE 2025"
	if parsed.Title != want {
		t.Fatalf("expected title %q, got %q", want, parsed.Title)
	}
}

func TestParseExtractsPublishedDateFromRealFixture(t *testing.T) {
	parsed, err := DOUParser{}.Parse(realFixture(t))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	want := time.Date(2025, time.January, 16, 0, 0, 0, 0, time.UTC)
	if !parsed.PublishedAt.Equal(want) {
		t.Fatalf("expected published date %v, got %v", want, parsed.PublishedAt)
	}
}

func TestParseExtractsFullTextFromRealFixture(t *testing.T) {
	parsed, err := DOUParser{}.Parse(realFixture(t))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	for _, phrase := range []string{"Contribuição sobre Bens e Serviços", "LUIZ INÁCIO LULA DA SILVA"} {
		if !strings.Contains(parsed.FullText, phrase) {
			t.Fatalf("expected full text to contain %q, it did not", phrase)
		}
	}
}

func TestParseAlwaysSetsSourceTypePrimary(t *testing.T) {
	parsed, err := DOUParser{}.Parse(realFixture(t))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if parsed.SourceType != domain.SourceTypePrimary {
		t.Fatalf("expected SourceType %q, got %q", domain.SourceTypePrimary, parsed.SourceType)
	}
}

func TestParseReturnsErrorWhenTextoDouIsMissing(t *testing.T) {
	_, err := DOUParser{}.Parse([]byte("<html><title>sem lei</title><body>nada aqui</body></html>"))
	if err == nil {
		t.Fatal("expected an error when .texto-dou is missing, got nil")
	}
}
