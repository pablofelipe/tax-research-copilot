# ADR-0006: Continuous Integration Scope

## Status

Accepted

## Context

Nothing in this repository runs in CI today — every test run so far has been manual, on the local machine, against local infrastructure (Docker Desktop's Postgres/Ollama). A real CI pipeline needs a clear answer to "what actually runs on every push," and that answer is constrained by a fact this project has already measured and documented: a single question through the full graph takes ~609 seconds on CPU-only Llama 3.1 8B (ADR-0001's Known Limitation amendment), making the real evaluation harness — by design meant to run repeatedly — impractical to run on every push, let alone the full 21-case dataset.

Unit tests need nothing external (they run against fakes throughout this codebase, both Python and Go). Integration tests need a real PostgreSQL/pgvector instance but not Ollama — they exercise `PgVectorChunkRepository`, `PostgresAuditRepository`, and the Go `storage` package's Postgres adapter, none of which call an LLM.

## Decision

GitHub Actions, two jobs, on every push and pull request:

**`python`**: `uv sync`, `uv run pytest tests/unit` (no external dependencies), then `uv run pytest tests/integration -m integration` against a PostgreSQL service container (`pgvector/pgvector:pg17`, the same image `docker-compose.yml` already uses) — the migrations (`migrations/*.sql`) are applied the same way the integration test fixtures already apply them, so no new tooling is needed to get the schema in place.

**`go`**: `go build ./...`, `go vet ./...`, `go test ./...` inside `services/ingestion/`, against the same PostgreSQL service container for `internal/storage`'s integration test (currently gated behind the `integration` build tag but not yet run anywhere).

**Not run in CI**: `app/evaluate.py` (the real evaluation harness) and anything else that calls Ollama. This is the direct, already-documented consequence of the per-case latency in ADR-0001's Known Limitation — running it in CI would make every push take hours, not verify anything additional that the unit-tested harness logic (`run_case`/`run_suite` against fakes) doesn't already cover.

## Consequences

**Positive**

- Every push gets real verification of both languages' unit and integration tests, including the previously-never-run Go integration test — closing a gap where `internal/storage`'s Postgres adapter had a real integration test that nothing ever executed outside a developer's own machine.
- No new infrastructure to maintain: the CI Postgres service container uses the exact image already used in `docker-compose.yml` and the integration tests' own migration-application logic, not a parallel setup.

**Negative**

- CI provides no automated signal on LLM-facing behavior (Planner/Researcher/Critic output quality, the Critic conflict-detection unreliability already documented as a known limitation) — that class of regression is caught only by a human running `app.evaluate` locally, not by CI.
- No cross-language trace verification in CI — OpenTelemetry instrumentation (ADR-0005) is exercised locally only, not asserted against in a CI job.

## Alternatives Considered

- **Running a reduced evaluation harness in CI** (e.g., `--limit 1`): rejected — even one case is ~609 seconds on CPU-only inference, and CI runners have no GPU; this would make every push slow for a check that doesn't test anything CI-unique (unit tests already cover the harness's own logic against fakes).
- **Skipping integration tests in CI, unit tests only**: rejected — the real Postgres/pgvector-backed adapters (`PgVectorChunkRepository`, `PostgresAuditRepository`, Go's `storage` package) have never been run in CI at all before this ADR; leaving them out would mean CI only re-verifies what unit tests already prove, not the actual database integration surface.
- **A hosted CI runner with GPU for real LLM checks**: rejected for v1 — real cost, and no evidence yet that CI-run LLM checks would catch something the documented known limitations haven't already surfaced through manual runs.
