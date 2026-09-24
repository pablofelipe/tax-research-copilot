package domain

import (
	"regexp"
	"testing"
)

func TestHashIsDeterministicForTheSameText(t *testing.T) {
	a := Document{FullText: "texto da lei"}.Hash()
	b := Document{FullText: "texto da lei"}.Hash()

	if a != b {
		t.Fatalf("expected same hash for identical text, got %q and %q", a, b)
	}
}

func TestHashChangesWhenTextChanges(t *testing.T) {
	a := Document{FullText: "texto da lei"}.Hash()
	b := Document{FullText: "texto da lei, com uma alteracao"}.Hash()

	if a == b {
		t.Fatalf("expected different hashes for different text, got the same: %q", a)
	}
}

func TestHashIsHexEncodedSHA256(t *testing.T) {
	hash := Document{FullText: "texto da lei"}.Hash()

	matched, err := regexp.MatchString("^[0-9a-f]{64}$", hash)
	if err != nil {
		t.Fatalf("regexp error: %v", err)
	}
	if !matched {
		t.Fatalf("expected a 64-char lowercase hex string, got %q", hash)
	}
}
