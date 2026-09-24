# ADR-0001: Multi-Step Tax Research Orchestration with LangGraph

## Status

Accepted

## Context

A prior project by the same author answers point-in-time questions against a single, stable, authoritative source (US Treasury exchange rate data), through a linear five-step pipeline (semantic retrieval, LLM rerank, structured output) with no cycles and no conditional branching. That decision — plain FastAPI orchestration, no agent framework — was made deliberately, not by default: the two reasons on record are that the problem has none of the complexity an orchestration framework earns its keep on (cycles, deep conditional branching, multiple coordinated agents), and that a plain stack trace is faster to debug than tracing execution across a graph's abstract nodes. That decision is documented publicly by the author, not as a numbered ADR in that project's repository. It stands on its own for the problem it was made for.

Tax Research Copilot targets a structurally different problem: Brazil's consumption tax reform (EC 132/2023, LC 214/2025) spans a multi-year transition (2026–2033), with sources that change over time and sometimes disagree with each other — statute text, subsequent infralegal regulation, and interpretive opinions published by law firms. Answering a non-trivial question in this domain requires:

- decomposing a complex question into independently verifiable sub-questions (retrieval is not a single call, it is N);
- detecting and surfacing disagreement between sources instead of silently picking one;
- carrying state across steps, where a later step depends on an earlier one and may need retry or correction;
- pausing mid-flow for human approval when confidence is low, not only reporting a final answer.

These four requirements are the actual justification for introducing an orchestration framework here. They do not apply to the single-source, point-query problem this author solved without one — the two decisions answer different problems and are not in tension with each other.

## Decision

Adopt LangGraph for multi-step orchestration, structured as a five-node state graph with PostgreSQL-backed checkpointing.

### Graph structure

1. **Planner** — decomposes the user's question into independent, verifiable sub-questions.
2. **Researcher** — retrieves cited excerpts per sub-question from the indexed corpus; no citation, no answer (unsupported claims are never produced).
3. **Critic** — verifies that each citation actually supports the claim made from it, and flags disagreement when two sources (e.g., statute text vs. a law firm's position) conflict on the same point.
4. **Evaluator** — aggregates confidence across sub-answers; below a configured threshold, forces a blocking pause for human review — not a best-effort suggestion.
5. **Report Generator** — produces a structured response, with a dedicated disputed-positions section whenever the Critic has flagged a conflict.

State is persisted through a LangGraph checkpointer backed by PostgreSQL, so a human-review pause survives a process restart without losing progress already made in earlier nodes.

### Output schema

```python
class SourceCitation(BaseModel):
    source_type: Literal["primary", "secondary"]  # primary = statute/official gazette/tax authority; secondary = law firm opinion
    document_id: str
    title: str
    published_at: date
    content_hash: str
    excerpt: str
    url: str | None

class SubAnswer(BaseModel):
    sub_question: str
    answer: str
    citations: list[SourceCitation]
    confidence: float

class DisputedPosition(BaseModel):
    topic: str
    positions: list[SubAnswer]   # conflicting sub-answers on the same topic, each with its own citation
    resolution_note: str | None  # context only, never a verdict — e.g. "tax authority has not yet published a position on this point"

class TaxResearchResponse(BaseModel):
    query: str
    sub_answers: list[SubAnswer]
    disputed_positions: list[DisputedPosition]
    overall_confidence: float
    requires_human_review: bool
    human_review_notes: str | None
    generated_at: datetime
```

`DisputedPosition` reuses `SubAnswer` rather than duplicating its shape: the Critic groups sub-answers that disagree on the same topic instead of producing a parallel structure for conflicts. The system never resolves a disputed position on its own — `resolution_note` carries context, never a decision, consistent with the rule that a secondary source's position is never presented as if it were normative text.

### Confidence threshold

Fixed at 0.7 for v1. Per-question-type configuration is explicitly deferred, not implemented, and tracked below as an open question for a future ADR.

### Vector store

pgvector, on the same PostgreSQL instance already required for checkpointing — rather than a separate ChromaDB instance or a dedicated vector database (e.g., Qdrant). Consolidating onto one already-required system is the more defensible choice here: it avoids operating a second stateful service for data that benefits from staying inside a single system boundary, and it produces a real architectural trade-off worth defending, rather than a default carried over from a prior project.

### Why ingestion is a separate Go service, not a Python module

Orchestration stays in Python because the tooling it depends on — LangGraph, the broader LLM/agent ecosystem — is Python-native; wrapping that from another language would add a translation layer for no benefit. Ingestion is a different shape of problem: fetching, hashing, and dating a growing set of source documents is concurrent I/O-bound work, independent of the graph's own execution, and does not need any LLM-specific tooling. Go's concurrency primitives fit that shape directly, and a statically compiled binary is a simpler deployable unit for a service with no Python-ecosystem dependency of its own. The two languages are split along this real boundary — LLM orchestration vs. concurrent I/O — not by layer for its own sake.

### Go ingestion service scope (v1)

Limited to source ingestion and versioning — fetching, hashing, and dating documents from official sources. MCP exposure is explicitly deferred to a future ADR. The service is designed with a clean domain interface (a source-repository port) so that adding an MCP adapter later requires only a new adapter behind the existing port, not a restructuring of the ingestion domain logic.

## Consequences

**Positive**

- Demonstrates genuine multi-step, stateful agent orchestration and human-in-the-loop as a first-class flow, not an unhandled exception path.
- Keeps the orchestration-framework decision scoped to the class of problem that actually requires it, so it does not contradict the framework-free decision made for a structurally different, single-source problem in the author's other project.
- Infra consolidation (one PostgreSQL instance for both checkpoints and vectors) is an explicit, defensible trade-off rather than an unexamined default.

**Negative**

- PostgreSQL becomes a more critical dependency (checkpoints and vectors together), increasing the blast radius of an outage compared to isolating vector storage in a separate service.
- Deferring MCP exposure means the Go service's tool-calling interface stays unproven until a later ADR forces it into existence; if a consumer-side requirement appears sooner than expected, this becomes a blocking dependency instead of parallel work.

**Deferred, not rejected**

- Configurable confidence threshold per question type.
- MCP exposure from the Go ingestion service.

## Alternatives Considered

- **No orchestration framework, hand-rolled control flow** (the approach used in the author's other project, for a different problem shape): rejected for this project — the requirement set (conditional branching, multi-step state with retry, a blocking human-review pause that survives a process restart) would mean re-implementing a smaller, less-tested version of what a purpose-built framework already provides.
- **ChromaDB**, reused from a prior project: rejected — would add no new architectural surface beyond what the author's existing project already demonstrates.
- **Qdrant**, a dedicated vector database: rejected for v1 — no requirement identified that PostgreSQL/pgvector cannot meet at this project's expected scale. Revisit if retrieval volume or vector-specific features (advanced filtering, multi-tenancy) later justify a dedicated service.
- **Full Go service scope including MCP exposure in v1**: rejected — no proven consumer-side requirement yet, and the planned domain boundary makes adding it later low-cost, so building it speculatively now is unjustified.

## Open Questions Tracked for Future ADRs

- Configurable confidence threshold per question type, once real usage data shows the fixed 0.7 threshold is too coarse.
- MCP exposure from the Go ingestion service, once a concrete consumer-side requirement exists on the Python/LangGraph side.
- Deriving Researcher confidence (partly or fully) from retrieval-quality signals once a concrete vector-store adapter exists (see Amendment below), rather than relying solely on LLM self-report.
- Whether Llama 3.1 8B's output quality (format compliance, groundedness) is sufficient once exercised against real retrieval data, or whether a hosted model becomes necessary for acceptable human-review rates — partially answered for the Critic's conflict detection specifically (see the Known Limitation amendment below); still open for the Planner and Researcher.
- Graceful handling of node errors (`PlannerError`/`ResearcherError`/`CriticError`) at the runtime entry point (`app/main.py`), which currently lets them propagate as an unhandled exception and crash the process instead of surfacing a readable message. Deferred until there is a real caller (a future API layer, or repeated CLI use) that needs better behavior than "the run failed, see the traceback."

## Amendment: Researcher Confidence Signal

Added during implementation of the Researcher node, not decided by the original text above.

The Researcher calls the retrieval port first; an empty result raises an error without ever calling the LLM — no citation means no answer, consistent with this ADR's Researcher guardrail. When citations are found, a single LLM call receives the sub-question and the retrieved excerpts and returns both the synthesized answer and a self-reported confidence value, bound to `[0, 1]` by the `SubAnswer` schema.

**Alternative considered**: derive confidence deterministically from a retrieval signal (e.g., citation count, retrieval score) instead of LLM self-report. Rejected for v1 — no retrieval implementation exists yet to produce a meaningful score, and citation count alone would not capture whether the excerpts actually support the specific claim made. Revisit once a concrete vector-store adapter exists (tracked above).

This is documented here rather than as a separate ADR because it changes the confidence signal the Evaluator's aggregation (ADR-0002) directly depends on — the same subject this ADR already governs.

## Amendment: Graph Wiring — Sequential Research and Interrupt-Based Human Review

Added when the five nodes were connected into an executable `StateGraph` (`app/graph/build.py`). Two decisions here are the concrete realization of promises this ADR already made, not new scope.

**Sequential research over sub-questions, not parallel fan-out.** The Researcher runs once per sub-question, in order, inside a single node. LangGraph supports parallel fan-out for exactly this shape (the `Send` API, dispatching one sub-graph invocation per sub-question concurrently). Sequential was chosen for v1: simpler failure handling (one `ResearcherError` stops the run at a predictable point, instead of requiring a policy for partial fan-out failures) and simpler ordering guarantees, at the cost of wall-clock latency scaling linearly with the number of sub-questions. Revisit if that latency becomes a real constraint — nothing about the node's own implementation needs to change, only how `research_node` invokes it.

**Human review is a blocking `interrupt()`, not a conditional branch to a terminal state.** After `evaluate`, a conditional edge routes to `human_review` when `requires_human_review` is true, otherwise straight to `report`. The `human_review` node calls LangGraph's `interrupt()`, which halts execution and — with a checkpointer — persists the full state so the pause survives a process restart; resuming requires an explicit `Command(resume=...)` from outside the graph, there is no timeout or automatic continuation. This is the literal mechanism satisfying this ADR's "blocking, not best-effort" requirement for human review. Without a checkpointer, `interrupt()` still halts a single `invoke()` call but cannot be resumed across process restarts — acceptable for the unit tests exercising this graph in-process, but a real deployment must always compile with a persistent checkpointer (PostgreSQL, per this ADR's original decision) for the guarantee to hold.

**Alternative considered** (human review): route to a terminal "needs_review" state and let a separate process pick it up later (polling a status field) instead of an in-graph blocking interrupt. Rejected — it would mean building a second, hand-rolled persistence/resumption mechanism on top of the one LangGraph's checkpointer already provides, which is exactly the kind of re-implementation this ADR's own "Alternatives Considered" section already rejected when it chose LangGraph over hand-rolled control flow.

## Amendment: LLM Provider — Llama 3.1 8B via Local Ollama

`LLMPort` was deliberately left provider-agnostic by this ADR, with no vendor chosen. For v1, that gap is filled: **Llama 3.1 8B, served locally through Ollama** (a new `ollama` service in `docker-compose.yml`, no GPU passthrough — the development machine's GPU has 2 GB of VRAM, not enough to matter, so inference runs on CPU).

**Why a local, zero-cost model instead of a hosted API** (Google Gemini, OpenAI, Anthropic Claude were the hosted alternatives considered): this project's own engineering discipline (documented separately from this ADR) already requires exhausting offline/zero-cost options before introducing API spend. A locally-served open-weight model costs nothing per call, which matters for a project in active, iterative development where the graph will be invoked many times while nodes and prompts are still being tuned. The trade-off accepted knowingly: Llama 3.1 8B is weaker than frontier hosted models at strict output-format compliance and at avoiding hallucination under a citation-grounding guardrail — exactly the property this system's guardrails depend on most. Because every node already treats malformed or ungrounded LLM output as a parseable failure (`PlannerError`/`ResearcherError`/`CriticError`, never a silent guess), a less reliable model degrades into more human-review pauses and more raised errors, not into silently wrong answers reaching a user — the schema-level guardrails (ADR-0002's confidence gating in particular) are what make a weaker model tolerable here.

**Why 8B and not a smaller or larger size**: 3B is faster on CPU but weaker at following the strict JSON-only instruction every node's prompt depends on; anything past ~8B (e.g., 70B-class models) is not feasible without GPU acceleration on this hardware (would require on the order of 40 GB+ of memory even quantized).

Swapping this for a hosted provider later is a new `LLMPort` implementation plus a wiring change at graph construction — no change to any node, port, or schema — by the same design that made this ADR defer the choice in the first place.

## Amendment: Retrieval Adapter — pgvector-Backed `RetrievalPort` with Ollama Embeddings

`RetrievalPort` was left provider-agnostic by this ADR, same as `LLMPort`. For v1, this is filled: a `RetrievalPort` adapter backed by pgvector (on the same PostgreSQL instance already chosen above), embedding both the indexed corpus and incoming queries with **`nomic-embed-text`, served locally through the same Ollama instance already running the chat model** — one embedding call per query, matching `OllamaClient`'s existing HTTP-call shape rather than introducing a second inference runtime.

**Why an Ollama-served embedding model instead of `sentence-transformers`** (an in-process Python library, and the choice already made in the author's other project): consolidating onto the Ollama service already running for the chat model avoids operating two separate local inference paths (an HTTP-served model and an in-process PyTorch model) for what is architecturally the same kind of work — this mirrors the reasoning that put both the checkpointer and the vector store on one PostgreSQL instance earlier in this ADR, applied to inference infrastructure instead of storage. The cost accepted: an extra local HTTP round-trip per embedding call versus an in-process function call, judged not to matter at this project's expected scale.

**Why `nomic-embed-text`**: 768-dimensional, small (~274 MB), and the most widely used general-purpose embedding model in the Ollama ecosystem — a reasonable default for CPU-only inference on this hardware (see the LLM Provider amendment above for the same hardware constraint). `mxbai-embed-large` (1024-dimensional, larger) was considered and rejected for v1 — no evidence yet that its marginal quality gain is worth the added CPU cost; revisit if retrieval quality proves insufficient once exercised against real questions.

Swapping either the embedding model or the vector-store adapter later is a new `RetrievalPort` implementation plus a wiring change — no change to any node, port, or schema — by the same design already established for `LLMPort`. Re-embedding the existing corpus is required on either kind of swap, since vector dimensionality and semantic space are model-specific; this cost is accepted as inherent to changing an embedding model, not specific to this choice.

## Known Limitation: Llama 3.1 8B's Unreliability at Conflict Detection

Observed running `app/main.py` end to end against the real indexed LC 214/2025 corpus (not a fabricated or curated test case): the Critic's `detect_conflicts` call repeatedly returned a conflict group naming only one sub-answer index, which `DisputedPosition`'s own validator correctly rejects (a disputed position requires at least two conflicting positions by definition). Before this was observed, that rejection surfaced as a raw `pydantic.ValidationError` instead of a `CriticError`, breaking this ADR's own guardrail that every node treats malformed LLM output as a parseable failure — fixed in the same session this was found, so the failure mode is now a clean, typed error again.

The underlying issue is not the error handling, though — it is Llama 3.1 8B itself: asked to find sub-answers that disagree with each other, it sometimes flags a single sub-answer as "conflicting" with nothing, a task-comprehension failure this ADR's LLM Provider amendment already flagged as a plausible-but-unconfirmed risk of choosing a small, zero-cost, CPU-only model. This is now a confirmed instance, specific to the conflict-detection call — the Planner (question decomposition) and Researcher (grounded synthesis) have not shown an equivalent failure in the same run.

**Not fixed for v1.** The correct system-level behavior when the Critic itself cannot be trusted is already consistent with this ADR's guardrails: `CriticError` propagates out of `critique_node` and the graph run fails loudly rather than silently accepting a malformed conflict — but nothing yet retries, falls back to "no conflict detected," or escalates automatically. Revisit once real usage volume shows whether this is rare enough to leave as a hard failure, or common enough to need either a stronger model for this specific call or a deterministic pre-filter (e.g., only ask the LLM about topics where sub-answers' cited documents actually differ) before trusting free-form conflict detection.

## Known Limitation: Per-Question Latency Makes a Full CI Evaluation Run Impractical

Measured running `app/evaluate.py` for real, one case, against the real corpus: a single question took 609 seconds end to end (plan → research → critique → evaluate → auto-resumed human review), all on CPU-only Llama 3.1 8B. This project's evaluation harness is meant to run in CI and compare agent versions over a versioned dataset; at this per-case latency, the 21-question dataset (`app/evaluation/dataset.json`) would take on the order of three and a half hours for a single full run, which is impractical both for local iteration and for a CI job.

This is the same root cause as the LLM Provider amendment's accepted trade-off (zero-cost, CPU-only local inference) surfacing in a different place: it was accepted for interactive development, but a full-suite evaluation run — by design, meant to run repeatedly to compare versions — amplifies it by the size of the dataset. **Not fixed for v1.** The harness itself (`run_suite`, `--limit` for a partial run) is real and works; running it in CI, or running the full dataset at all, is deferred until either a faster inference path exists for evaluation specifically (a hosted model used only for CI runs, keeping the zero-cost local model for interactive use) or the dataset is intentionally kept small enough to stay practical.

## Amendment: Intent Guardrail Before Retrieval

This project's declared domain (the Brazilian consumption tax reform — EC 132/2023, LC 214/2025 and its infralegal follow-on, explicitly excluding income tax, labor tax, court case law, and binding legal opinions, per the Scope section of the README) needs a guardrail rejecting an out-of-scope question before it ever reaches retrieval or the LLM — otherwise every query, however unrelated, would spend a real LLM call decomposing it into sub-questions.

**Decision**: a keyword-based `Guardrail.is_in_scope()` check, matched against a fixed, accent/case-insensitive list of terms drawn directly from the domain definition (IBS, CBS, Imposto Seletivo, EC 132, LC 214, split payment, etc.) — not an LLM call. `Guardrail.reject()` returns a new `OutOfScopeResponse` schema (`query`, `message`, `generated_at`), deliberately without a citations field: forcing a rejection into `TaxResearchResponse`'s shape would require fabricating at least one citation to satisfy that schema's own guardrail (`SubAnswer` requires ≥1 citation), which would defeat the whole point of rejecting before retrieval.

**Why keyword matching instead of an LLM-based classifier**: an LLM call to classify intent would itself be the retrieval-adjacent cost this guardrail exists to avoid — a classifier call is still a call. A fixed keyword list is zero-cost, deterministic, and trivially testable, at the cost of being coarser than a semantic classifier (a well-phrased in-scope question using none of the listed terms would be misclassified as out of scope). Accepted for v1: false negatives here fail safe (an in-scope question gets rejected, not an out-of-scope one silently answered), and the term list is drawn from this project's own domain definition, not guessed.

**Wiring**: `START` routes to a `guardrail` node first, with a conditional edge to either `plan` (in scope) or a terminal `out_of_scope` node returning the `OutOfScopeResponse` directly — the same conditional-edge pattern already used for `route_after_evaluate`'s human-review branch. An out-of-scope query never reaches `plan`, `research`, or any other node that would call the LLM or `RetrievalPort`.
