package ingest

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os/exec"
	"testing"
)

func requireCurl(t *testing.T) {
	t.Helper()
	if _, err := exec.LookPath("curl"); err != nil {
		t.Skip("curl binary not found in PATH, skipping")
	}
}

func TestCurlFetchReturnsBodyOnSuccess(t *testing.T) {
	requireCurl(t)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("conteudo via curl"))
	}))
	defer server.Close()

	fetcher := NewCurlFetcher()

	body, err := fetcher.Fetch(context.Background(), server.URL)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if string(body) != "conteudo via curl" {
		t.Fatalf("unexpected body: %q", body)
	}
}

func TestCurlFetchSendsABrowserUserAgent(t *testing.T) {
	requireCurl(t)

	var receivedUserAgent string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedUserAgent = r.Header.Get("User-Agent")
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	fetcher := NewCurlFetcher()
	if _, err := fetcher.Fetch(context.Background(), server.URL); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if receivedUserAgent != browserUserAgent {
		t.Fatalf("expected User-Agent %q, got %q", browserUserAgent, receivedUserAgent)
	}
}

func TestCurlFetchReturnsErrorOnNonOKStatus(t *testing.T) {
	requireCurl(t)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	fetcher := NewCurlFetcher()

	if _, err := fetcher.Fetch(context.Background(), server.URL); err == nil {
		t.Fatal("expected an error for a non-200 response, got nil")
	}
}
