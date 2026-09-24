# ADR-0005: OpenTelemetry Instrumentation

## Status

Accepted

## Context

Every graph node needs a real, queryable span, not decorative logging, and the intent was for a trace to be propagated across the Python → Go boundary. That second half no longer describes this project's actual architecture: the Go ingestion service is a standalone CLI, run offline to fetch and version source documents (`services/ingestion/cmd/ingest`) — it is never called synchronously by the Python graph at request time (MCP exposure, the mechanism that would make that a live call, was explicitly deferred in ADR-0001). There is no call boundary between Python and Go to propagate a trace across, because Go is not in the request path of a graph run at all.

This ADR instruments both sides for real, honestly scoped to what each one actually does: spans across the graph's nodes for a Python run, and spans across the ingestion CLI's own steps for a Go run — as two independently useful traces in the same backend, not one trace pretending to cross a boundary that doesn't exist yet.

## Decision

### Exporter: local Jaeger via docker-compose

A `jaeger` service (the `jaegertracing/all-in-one` image) added to `docker-compose.yml`, receiving spans over OTLP and serving a real query UI — free, self-hosted, consistent with this project's existing local-first infrastructure (PostgreSQL, Ollama). Both the Python and Go sides export to it.

### Python: one span per graph node, one root span per `invoke()` call

A single tracer, initialized once in `app/main.py`/`app/evaluate.py` (the composition roots). Each node function registered in `build_graph` (`guardrail`, `plan`, `research`, `critique`, `evaluate`, `human_review`, `report`, `out_of_scope`) is wrapped in its own span at the point it's added to the graph — a thin wrapper at the wiring layer in `app/graph/build.py`, not a change to any node class itself, so `Planner`/`Researcher`/`Critic`/etc. and their existing fake-backed unit tests are untouched. Each `graph.invoke()` call gets its own root span named `graph_run`; the node spans it contains are its children.

**Scoping note**: a human-review pause and its later resume are two separate `invoke()` calls (LangGraph's own execution model — see ADR-0001's Graph Wiring amendment), so they produce two separate root spans, not one span spanning the whole pause-then-resume saga. Linking them into a single logical trace would need LangGraph's own run id threaded through as a span attribute; deferred, tracked below.

### Go: one span per ingest step, its own root span per CLI invocation

`cmd/ingest`'s `main` starts a root span (`ingest_run`); `Fetch`, `Parse`, and the repository's `Exists`/`Save` calls each get a child span. This is a separate trace from any Python run — there is no propagation between them, for the reason in Context above.

### Dependencies

Python: `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http`. Go: `go.opentelemetry.io/otel`, `go.opentelemetry.io/otel/sdk`, and the OTLP HTTP exporter — both are the standard, uncontroversial SDKs for their language, not a contested choice.

## Consequences

**Positive**

- Every graph node and every ingestion step now has a real, inspectable span in a real backend, closing this project's declared observability gap instead of leaving it decorative.
- Node classes and their existing unit tests are untouched — instrumentation lives entirely at the two composition-root/wiring layers (`app/graph/build.py`, `cmd/ingest/main.go`).

**Negative**

- No cross-language trace correlation exists yet — a Python run and a Go ingestion run are two unrelated traces in the same Jaeger instance, not one trace with two service hops. This is an accurate reflection of the current architecture, not a missing feature of the instrumentation itself.
- A paused-then-resumed human-review run produces two disconnected root spans instead of one continuous trace of the whole decision.

## Alternatives Considered

- **Faking Python → Go propagation** (e.g., injecting a trace context into the ingestion CLI's environment even though nothing calls it live): rejected — would produce a trace that looks connected but represents a call that never happens, actively misleading whoever reads it.
- **A hosted/managed tracing backend** (Honeycomb, Datadog, etc.): rejected for v1 — introduces real cost and an external dependency this project's zero-cost-first discipline doesn't yet justify; Jaeger self-hosted meets the same instrumentation goal for nothing.
- **Console/stdout span exporter**: rejected — spans would exist but not be queryable or visually inspectable, which undercuts the point of "real, not decorative" observability from the requirement this ADR closes.

## Open Questions Tracked for Future ADRs

- Linking a paused run's two root spans (initial `invoke()` and the later `Command(resume=...)` `invoke()`) into one logical trace, once LangGraph's run/thread id is threaded through as a span attribute.
- Real Python → Go trace propagation, once the Go service is actually called live from the Python side (e.g., if/when MCP exposure from ADR-0001's deferred scope is built).
