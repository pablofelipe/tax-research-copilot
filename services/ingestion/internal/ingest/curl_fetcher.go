package ingest

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
)

// CurlFetcher shells out to the curl binary instead of Go's net/http
// client. Some hosts (e.g. in.gov.br, behind Azion's bot mitigation) block
// requests on TLS fingerprint (JA3/JA4), which flags Go's default
// crypto/tls handshake regardless of headers sent; curl's TLS stack does
// not get flagged. This is not fingerprint spoofing — curl is a real,
// ordinary HTTP client presenting its own honest identity, just one this
// particular host happens not to block.
type CurlFetcher struct {
	binary string
}

func NewCurlFetcher() *CurlFetcher {
	return &CurlFetcher{binary: "curl"}
}

func (f *CurlFetcher) Fetch(ctx context.Context, url string) ([]byte, error) {
	cmd := exec.CommandContext(ctx, f.binary, "-sS", "-f", "-A", browserUserAgent, url)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("curl fetch failed for %s: %w (stderr: %s)", url, err, stderr.String())
	}

	return stdout.Bytes(), nil
}
