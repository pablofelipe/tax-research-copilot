package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"go.opentelemetry.io/otel"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/ingest"
	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/observability"
	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/storage"
)

func main() {
	url := flag.String("url", "", "URL of the DOU page to ingest (required)")
	documentID := flag.String("document-id", "", "stable identifier for this document, e.g. lc-214-2025 (required)")
	databaseURL := flag.String("database-url", "postgres://tax_research:tax_research@localhost:5432/tax_research", "PostgreSQL connection string")
	otlpEndpoint := flag.String("otlp-endpoint", observability.DefaultOTLPEndpoint, "OTLP HTTP endpoint for trace export")
	flag.Parse()

	if *url == "" || *documentID == "" {
		fmt.Fprintln(os.Stderr, "usage: ingest --url <dou-page-url> --document-id <id>")
		os.Exit(2)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	shutdownTracing, err := observability.Setup(ctx, "tax-research-copilot-ingestion", *otlpEndpoint)
	if err != nil {
		log.Fatalf("configuring tracing: %v", err)
	}
	defer shutdownTracing(context.Background())

	pool, err := pgxpool.New(ctx, *databaseURL)
	if err != nil {
		log.Fatalf("connecting to postgres: %v", err)
	}
	defer pool.Close()

	// CurlFetcher, not HTTPFetcher: in.gov.br blocks Go's net/http client on
	// TLS fingerprint (see curl_fetcher.go).
	service := ingest.NewService(
		ingest.NewCurlFetcher(),
		ingest.DOUParser{},
		storage.NewPostgresRepository(pool),
	)

	ctx, rootSpan := otel.Tracer("tax_research_copilot.ingestion").Start(ctx, "ingest_run")
	err = service.Ingest(ctx, *url, *documentID)
	rootSpan.End()
	if err != nil {
		log.Fatalf("ingest failed: %v", err)
	}

	fmt.Printf("ingested %q from %s\n", *documentID, *url)
}
