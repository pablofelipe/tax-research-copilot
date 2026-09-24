# Tax Research Copilot

A multi-step research assistant for Brazil's consumption tax reform (EC 132/2023, LC 214/2025, and the infralegal regulation that follows it through the 2026–2033 transition).

## Scope

A question in this domain typically requires synthesizing several sources that change over time and sometimes disagree — statute text, subsequent regulation, and interpretive positions published by law firms. This project decomposes such a question into independently verifiable sub-questions, retrieves cited excerpts for each one, flags disagreement between sources instead of silently picking one, and pauses for human review when confidence is low.

**Out of scope**: tax law outside the consumption reform (income tax, labor tax, etc.), court case law, and binding legal opinions — the system cites and synthesizes sources, it does not replace a legal opinion.

## Architecture

A five-node state graph (Planner → Researcher → Critic → Evaluator → Report Generator), orchestrated with LangGraph and checkpointed to PostgreSQL, so a human-review pause survives a process restart. The LLM is Llama 3.1 8B served locally through Ollama, and retrieval is backed by pgvector with embeddings from nomic-embed-text (also served locally through Ollama). Source ingestion and versioning run as a separate Go service. See [`docs/adr/`](docs/adr/) for the full architectural record:

- [ADR-0001](docs/adr/0001-langgraph-orchestration-for-multi-step-tax-research.md) — why LangGraph, the graph structure, the output schema, the confidence threshold, the vector store choice, and the Go service's v1 scope.
- [ADR-0002](docs/adr/0002-evaluator-confidence-aggregation.md) — how the Evaluator aggregates sub-answer confidence and when it forces human review.

## Getting started

```bash
uv sync
docker compose up -d                                  # PostgreSQL + pgvector, and Ollama
docker exec tax-research-copilot-ollama-1 ollama pull llama3.1:8b
docker exec tax-research-copilot-ollama-1 ollama pull nomic-embed-text
uv run pytest
```

## Status

Early development. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the current checklist of what's done, in progress, and pending.
