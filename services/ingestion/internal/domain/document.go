package domain

import (
	"crypto/sha256"
	"encoding/hex"
	"time"
)

type SourceType string

const (
	SourceTypePrimary   SourceType = "primary"
	SourceTypeSecondary SourceType = "secondary"
)

type Document struct {
	DocumentID  string
	SourceType  SourceType
	Title       string
	PublishedAt time.Time
	FullText    string
	URL         string
}

// Hash is a hex-encoded SHA-256 of FullText, used to detect whether a
// source changed since it was last ingested.
func (d Document) Hash() string {
	sum := sha256.Sum256([]byte(d.FullText))
	return hex.EncodeToString(sum[:])
}
