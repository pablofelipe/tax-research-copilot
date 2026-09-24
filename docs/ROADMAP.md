# Roadmap

High-level status of the project. Updated as work lands — same discipline as the README-per-ADR rule (CLAUDE.md Section 7).

## Done

- Domain contracts (`SourceCitation`, `SubAnswer`, `DisputedPosition`, `TaxResearchResponse`) with the confidence-gating and citation guardrails enforced at the schema level.
- Domain ports (`LLMPort`, `RetrievalPort`), provider-agnostic by design.
- The five graph nodes (Planner, Researcher, Critic, Evaluator, Report Generator), each unit-tested against test doubles.
- The nodes wired into an executable LangGraph `StateGraph`, including the blocking human-review `interrupt()`.
- `OllamaClient`, a real `LLMPort` adapter backed by a local Llama 3.1 8B model (see ADR-0001's LLM Provider amendment).
- Go ingestion service (`services/ingestion/`) — fetches, hashes, and versions real source documents into a `source_documents` table in PostgreSQL. First real target: the DOU (Diário Oficial da União) publication of LC 214/2025, chosen over the Planalto `ccivil_03` consolidated text because it is the as-published, dated primary source the project's point-in-time requirement (CLAUDE.md Section 4) needs. Verified end to end against the real page (757,274 characters ingested, re-running is a no-op).
- Python retrieval adapter — `EmbeddingPort`/`OllamaEmbeddingClient` (nomic-embed-text via the same local Ollama instance), pure `chunk_text`, `Indexer` (chunk → embed → persist), `ChunkRepository` port with a real `PgVectorChunkRepository` (pgvector, cosine similarity, HNSW index), and `PgVectorRetrievalAdapter` implementing `RetrievalPort` (see ADR-0001's Retrieval Adapter amendment). Verified end to end against the real LC 214/2025 text: 545 chunks indexed, a real Portuguese question about the CBS reference rate returned on-topic cited excerpts from the actual statute text.
- Runtime entry point (`app/main.py`) — a CLI wiring the compiled graph to the real adapters (`OllamaClient`, `PgVectorRetrievalAdapter`, `PostgresSaver`), able to ask a question and resume a paused human-review thread. Run end to end against the real corpus: planning and grounded research completed with real LLM/retrieval calls; the Critic's conflict detection proved unreliable with Llama 3.1 8B on real data (see ADR-0001's Known Limitation amendment) — this is now a clean `CriticError`, not a crash, but node errors still propagate as an unhandled exception at the CLI level rather than a readable message (tracked as an open question in ADR-0001).
- Evaluation harness — `EvaluationCase`/`CaseResult`/`SuiteResult`, `run_case`/`run_suite` (groundedness against expected document ids, required-keyword matching, latency per full run), a 21-question versioned dataset (`app/evaluation/dataset.json`, every required keyword verified to literally appear in the real LC 214/2025 text before being added), `LangGraphRunner` (auto-resumes a human-review pause so evaluation always grades a final response), and `app/evaluate.py` as the real runtime entry point. Verified for real: one case passed end to end (grounded, keyword found) in ~609s on CPU-only Llama 3.1 8B — see ADR-0001's Known Limitation amendment on why running the full 21-case dataset (let alone in CI) is impractical on this hardware today.

## Pending

- OpenTelemetry spans per graph node, trace propagated across the Python → Go boundary.
- Audit trail persistence (every graph execution logged in a reconstructible way).
- Deployment/runtime packaging (not yet designed).
