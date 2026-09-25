# ADR-0003: Local Container Packaging for the Python and Go Services

## Status

Accepted

## Context

`docker-compose.yml` already runs PostgreSQL/pgvector and Ollama as long-running services. The Python graph (`app/`) and the Go ingestion service (`services/ingestion/`) still run only natively on the host — `uv run python -m app.main`, `go run ./cmd/ingest`. Neither has a container image, so there is no way to run the whole system (infra + application code) without a local Python/Go toolchain installed, and no path toward running this anywhere other than the current development machine.

Both application services are CLI-shaped, not long-running servers: `app.main`, `app.evaluate`, and the Go `ingest` command each do one unit of work and exit. There is no HTTP API in this project yet. This matters for how they fit into `docker-compose.yml` — they are not a natural fit for `docker compose up -d` the way Postgres and Ollama are.

## Decision

Add a Dockerfile for each application service, and add them to `docker-compose.yml` under the `tools` [profile](https://docs.docker.com/compose/how-tos/profiles/), so the existing `docker compose up -d` (documented in the README, already relied on by every session so far) keeps starting only Postgres and Ollama by default. The application containers are invoked on demand with `docker compose run --rm <service> <args>`, matching their actual CLI shape instead of forcing a fake "always-on" service around a one-shot command.

### Python image (`Dockerfile`, repo root)

Multi-stage build: an install stage using `ghcr.io/astral-sh/uv` to resolve and install dependencies via `uv sync --frozen`, then a slim `python:3.12-slim` runtime stage copying only the installed virtualenv and `app/`. Entrypoint is left unset — the command (`python -m app.main "..."` or `python -m app.evaluate --limit N`) is supplied by `docker compose run`, since both entry points are equally valid ways to invoke this image.

### Go image (`services/ingestion/Dockerfile`)

Multi-stage build: a `golang:1.23-alpine` builder stage running `go build ./cmd/ingest`, then a minimal runtime stage (`alpine`, not distroless) copying only the compiled binary — `alpine` chosen over distroless specifically because `CurlFetcher` shells out to the real `curl` binary (see the DOU TLS-fingerprint decision already in this codebase), which a distroless image does not have and would need to bundle in some other way.

### Networking

Containers reach Postgres and Ollama by their Compose service DNS names (`postgres`, `ollama`) on the Compose network, not `localhost`. Every entry point already takes `--database-url`/`--ollama-url` (Python) or `--database-url` (Go) as flags with a `localhost`-based default for native/host execution; running via `docker compose run` requires passing the in-network hostnames explicitly (documented in the README), rather than changing the defaults, so native execution (the primary workflow so far) is unaffected.

## Consequences

**Positive**

- The whole system — infra and application code — can run from a single `docker compose` invocation, with no local Python or Go toolchain required.
- `docker compose up -d` keeps its existing, already-documented meaning (Postgres + Ollama only); nothing about the established workflow changes for anyone not opting into the new images.
- The Go image's `alpine`-not-distroless choice is a direct, traceable consequence of an existing decision (`CurlFetcher`) rather than a new one made in isolation.

**Negative**

- Two Dockerfiles to keep in sync with dependency changes (`uv.lock`, `go.mod`), on top of the two native toolchains already required for local development — a small but real maintenance surface.
- `docker compose run` for a one-shot CLI is less discoverable than `docker compose up -d` for readers unfamiliar with Compose profiles; mitigated by documenting the exact commands in the README.

## Alternatives Considered

- **A single monorepo Dockerfile building both languages**: rejected — the two services already have an independent deployable boundary (separate Go module, separate `pyproject.toml`); a shared build stage would couple their release cadence for no benefit.
- **Making the application containers long-running services under `docker compose up -d`** (e.g., a Python container that sleeps, `exec`'d into for each command): rejected — it would misrepresent what these programs are (one-shot CLIs, not servers) and add a fake liveness/health story for a container that isn't actually serving anything.
- **Distroless runtime image for Go**: rejected for now — would break `CurlFetcher`'s dependency on the real `curl` binary; revisit if that fetcher is ever replaced or curl is vendored into the image separately.

## Open Questions Tracked for Future ADRs

- Real deployment (a hosted target, secrets management, exposing an HTTP API) is explicitly out of scope here — this ADR only covers running the existing CLIs in containers on a local machine, per the scope agreed with the user. Resolved by [ADR-0007](0007-hosted-demo-deployment.md), which adds an HTTP entry point and a hosting target.
