# Disclaimer

Tax Research Copilot is a software project for synthesizing and cross-referencing publicly available sources about Brazil's consumption tax reform (EC 132/2023, LC 214/2025, and its infralegal regulation). It is **not**, and does not substitute for:

- Legal advice or a formal legal opinion (*parecer jurídico*).
- Tax advice from a licensed accountant (*contador*) or tax attorney.
- An authoritative or official interpretation of any statute, regulation, or Comitê Gestor do IBS ruling.

## What this system does and does not guarantee

- Every answer is grounded in retrieved excerpts from indexed source documents, with a mandatory citation (document, publication date, content hash) — if no source is found, the system returns "not found," never a paraphrase invented without a citation.
- A response below the configured confidence threshold is never delivered without an explicit human-review pause.
- None of the above makes an answer legally authoritative. Statutory text, subsequent regulation, and interpretive positions from law firms can change, conflict, or be superseded — always verify against the current official source (Diário Oficial da União, Portal Planalto, Receita Federal) and, for any decision with real financial or legal consequences, consult a qualified professional.

## Scope

This project only covers the consumption tax reform (EC 132/2023, LC 214/2025 and its follow-on regulation). It explicitly does not cover income tax, labor tax, court case law, or any other area of Brazilian tax law — a question outside that scope is rejected before any retrieval or LLM call (see [ADR-0001](docs/adr/0001-langgraph-orchestration-for-multi-step-tax-research.md)'s Intent Guardrail amendment), not answered from general knowledge.

## No warranty

This software is provided under the Apache License 2.0, which includes an explicit disclaimer of warranties (see [LICENSE](LICENSE), Sections 7–8). Use it at your own risk.
