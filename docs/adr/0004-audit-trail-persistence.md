# ADR-0004: Audit Trail Persistence

## Status

Accepted

## Context

Every graph run needs to be logged in a way that can be reconstructed later: the question asked, the sub-questions the Planner derived, which sources were actually cited, the confidence decision, and the human decision when a pause happened. Nothing does this today — the LangGraph checkpointer persists state to resume a paused run, but it is not built to be queried afterward as a record of what happened; it is resumption state, not an audit log.

The human decision on a paused run is known only outside the graph: `app/main.py` calls `graph.invoke(...)`, sees `__interrupt__`, and later calls `graph.invoke(Command(resume=...))` with the decision. So "record this run" cannot be a graph node — it has to wrap the whole run from the composition root, after the final response (rejected, auto-approved, or resumed) is known.

## Decision

A new `audit_log` table on the same PostgreSQL instance already used for checkpoints and vectors (consistent with this project's existing consolidation reasoning). One row per completed run — including an out-of-scope rejection — written from `app/main.py` after the final response is available, not from inside the graph.

### What gets recorded

`thread_id`, `query`, `in_scope`, `sub_questions`, `citations` (document id, title, content hash — the same fields already carried on `SourceCitation`, not the full excerpt text, to keep rows small), `disputed_topics`, `overall_confidence`, `requires_human_review`, `human_decision` (the string passed to `Command(resume=...)`, `null` if no pause happened), `recorded_at`.

### Where the record is built

A pure function, `build_audit_record(thread_id, query, response, human_decision, clock)`, turns either response type (`TaxResearchResponse` or `OutOfScopeResponse`) into an `AuditRecord`, handling the out-of-scope case (no sub-questions, no citations, no confidence) as a normal branch rather than a special case elsewhere. This keeps the extraction logic unit-testable without a database, the same split already used for the retrieval adapter (`Indexer`/`PgVectorRetrievalAdapter` vs. `PgVectorChunkRepository`).

### Repository

`AuditRepository` port (`record(entry: AuditRecord) -> None`), with a real `PostgresAuditRepository` adapter — same tiering as `ChunkRepository`/`PgVectorChunkRepository`: the port and record-building logic are unit-tested against fakes, the concrete Postgres adapter is exercised by a real integration test against the docker-compose database.

## Consequences

**Positive**

- Every completed run — including a rejected out-of-scope query — leaves a reconstructible row, satisfying the audit requirement without adding a new stateful service.
- Reuses the existing single-Postgres consolidation instead of introducing a separate logging system.

**Negative**

- A run that pauses for human review and is never resumed leaves no row at all — only completed runs are recorded, not in-flight pauses. Accepted for v1: the LangGraph checkpointer already holds the in-flight state for a pause that's still open; the audit log's job is a record of finished decisions, not a second copy of resumable state.
- `citations` and `sub_questions` are stored as JSON columns, not normalized tables — fine at this project's expected scale (one row per run, not per citation), but not queryable with a relational join if that's ever needed later.

## Alternatives Considered

- **Logging from inside the graph** (a node after `report`/`out_of_scope`): rejected — the human decision on a resumed run is only known outside the graph, at the point `app/main.py` calls `Command(resume=...)`, so a graph-internal node could never see it for a resumed run.
- **Reusing the LangGraph checkpointer's own storage as the audit trail**: rejected — the checkpointer's schema and retention are owned by LangGraph for resumption, not designed to be queried as a human-readable history, and coupling this project's audit requirement to that internal schema would break on a LangGraph upgrade.
- **A separate logging/observability service** (e.g., shipping structured logs to an external sink): rejected for v1 — no such service exists in this project yet, and a Postgres table is a simpler, already-available place to put a small number of rows per run.
