package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/ingest"
	"github.com/pablofelipe/tax-research-copilot/services/ingestion/internal/storage"
)

func main() {
	url := flag.String("url", "", "URL of the DOU page to ingest (required)")
	documentID := flag.String("document-id", "", "stable identifier for this document, e.g. lc-214-2025 (required)")
	databaseURL := flag.String("database-url", "postgres://tax_research:tax_research@localhost:5432/tax_research", "PostgreSQL connection string")
	flag.Parse()

	if *url == "" || *documentID == "" {
		fmt.Fprintln(os.Stderr, "usage: ingest --url <dou-page-url> --document-id <id>")
		os.Exit(2)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

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

	if err := service.Ingest(ctx, *url, *documentID); err != nil {
		log.Fatalf("ingest failed: %v", err)
	}

	fmt.Printf("ingested %q from %s\n", *documentID, *url)
}
