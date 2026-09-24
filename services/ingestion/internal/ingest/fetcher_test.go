package ingest

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestFetchReturnsBodyOnSuccess(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("conteudo da pagina"))
	}))
	defer server.Close()

	fetcher := NewHTTPFetcher(server.Client())

	body, err := fetcher.Fetch(context.Background(), server.URL)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if string(body) != "conteudo da pagina" {
		t.Fatalf("unexpected body: %q", body)
	}
}

func TestFetchSendsABrowserUserAgent(t *testing.T) {
	var receivedUserAgent string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedUserAgent = r.Header.Get("User-Agent")
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	fetcher := NewHTTPFetcher(server.Client())
	if _, err := fetcher.Fetch(context.Background(), server.URL); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if receivedUserAgent == "" || receivedUserAgent == "Go-http-client/1.1" {
		t.Fatalf("expected a browser-like User-Agent, got %q", receivedUserAgent)
	}
}

func TestFetchReturnsErrorOnNonOKStatus(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	fetcher := NewHTTPFetcher(server.Client())

	if _, err := fetcher.Fetch(context.Background(), server.URL); err == nil {
		t.Fatal("expected an error for a non-200 response, got nil")
	}
}
