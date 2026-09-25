# ADR-0007: Hosted Demo Deployment on OCI with a Hosted LLM Provider

## Status

Accepted

## Context

ADR-0003 deliberately scoped out real deployment, deferring it until the project had "an HTTP entry point and a real hosting target." Both conditions are now driving a concrete need: a live, link-shareable instance that an external visitor can use to evaluate the project directly, alongside the source repository.

Two constraints shape this decision:

1. **Must be cloud-hosted, not local.** There is no personal server to run this on, and depending on a personal machine being online is not acceptable.
2. **CPU-only local inference (Llama 3.1 8B via Ollama) is not viable for this audience.** A single question already takes several minutes end to end on the development machine (documented in ADR-0001's Known Limitations and in `TROUBLESHOOTING.md`). Someone evaluating a link is not going to wait that long — the hosted demo needs response times on the order of seconds, not minutes.

A third constraint came out of a deliberate skeptical review of the access-control approach. A design built around automated, per-visitor credential issuance and expiry was considered and set aside — the concrete problems raised:

- Disproportionate engineering effort (a full credential lifecycle system) for a low-volume audience.
- OCI's Always Free tier is known to reclaim instances that show sustained low CPU usage — a demo nobody visits for a stretch of time could silently disappear exactly when someone finally tries it.
- A credential that leaves the owner's control automatically (rather than being handed out deliberately) is one accidental forward or screenshot away from being used by someone else, consuming API quota that should be reserved for the intended visitor.
- HTTP Basic Auth's native browser prompt, arriving cold via a link, has a real chance of being mistaken for phishing and ignored.
- A public LLM endpoint invites prompt-injection/jailbreak attempts for their own sake, and a bad screenshot from that is reputational risk this project doesn't need to take on.

The resulting approach: a single shared credential, manually rotated, provisioned on request — a link/form that notifies the owner, who generates and sends the credential by hand.

## Decision

### Hosting target: OCI Always Free tier

An Oracle Cloud Infrastructure "Always Free" compute instance (Ampere ARM, `VM.Standard.A1.Flex`, up to 2 OCPUs / 12 GB RAM in the free allocation) runs the existing `docker-compose.yml` stack. Chosen over Google Cloud / Azure because OCI's free tier is a permanent allocation, not a 12-month trial. Known risks, both without full solutions here: Oracle reclaims Always Free instances showing sustained near-zero CPU/network/memory usage over a 7-day window, and the Ampere shape's free capacity is not always available at instance-creation time in a given availability domain, requiring retries; tracked as open items below.

### HTTP entry point

A minimal FastAPI wrapper around the existing `graph.invoke()` call (already used by `app/main.py`), exposing a single endpoint that accepts a question and returns the structured `TaxResearchResponse`. This is new surface area — the graph, adapters, and core domain are unchanged; the wrapper is a thin composition-layer addition, the same way `app/main.py` and `app/evaluate.py` are today, not a rewrite of either.

### LLM provider for the hosted demo only: Groq

`LLMPort` (the existing port `OllamaClient` implements) gets a second adapter, `GroqClient`, calling Groq's OpenAI-compatible chat completions API. This is a hosted-environment-only substitution, selected via configuration/environment variable — native and containerized local runs keep using `OllamaClient` unchanged, and the domain/graph code has no knowledge of which adapter is active.

The model is `openai/gpt-oss-20b`, not the Llama 3.1 8B used by the evaluation dataset: Groq deprecated `llama-3.1-8b-instant` on its free/developer tier in mid-2026 (enterprise-contract access only), and recommends `openai/gpt-oss-20b` as the direct replacement. This means the hosted demo's model has not gone through this project's evaluation dataset — acceptable for a demo whose purpose is showing the system working end to end quickly, not for measuring answer quality, but worth being explicit about rather than implying parity with the evaluated model.

Embeddings stay on local Ollama (`nomic-embed-text`) inside the same container stack: embedding inference is fast even on CPU (unlike autoregressive chat generation), and Groq does not serve embedding models, so there is no equivalent hosted swap to make there.

Groq was chosen over other low-cost hosted options (DeepSeek, Qwen/Alibaba) mainly to avoid routing project traffic through infrastructure operated in China — not a technical concern given the public, non-sensitive nature of the ingested content, but a reasonable thing to avoid when the audience may notice and ask about it.

### Access control

A single shared HTTP Basic Auth credential, sitting behind a Caddy reverse proxy that also terminates HTTPS automatically (Let's Encrypt). The credential is rotated by a manual script run periodically by the project owner — not by an automated per-visitor lifecycle. Provisioning is on request: a link/form asks a visitor to request access, which notifies the owner, who sends the current credential manually.

### Hardening

- Per-IP rate limiting at the Caddy layer, bounding both abuse and accidental cost from a leaked credential.
- A usage cap/alert configured on the Groq API key, as a backstop against the worst case (a credential used well beyond its intended single-visitor scope).

## Consequences

**Positive**

- Removes the CPU-latency problem entirely for the audience that matters, without touching the local, zero-cost development workflow.
- `LLMPort` already being a port (not a concrete dependency) means adding `GroqClient` is additive — no change to `app/graph/`, `app/core/`, or any existing test double.
- Manual, request-based provisioning avoids building and maintaining a credential lifecycle system for a very low-volume, low-certainty audience.
- Zero infrastructure cost via OCI Always Free; the only recurring cost is bounded Groq API usage, capped explicitly.

**Negative**

- Introduces a live system the project now has to keep working (TLS renewal, container updates, Groq key rotation) — a maintenance surface that didn't exist before, and that can fail silently between uses.
- OCI's idle-reclaim behavior is a real, unmitigated risk: a demo nobody visits for long enough could disappear without the owner noticing until someone reports it.
- Manual credential provisioning does not scale past a handful of requests at a time — acceptable at expected volume, but a deliberate trade-off, not an oversight.
- A public LLM endpoint remains a target for prompt-injection/jailbreak attempts regardless of access control; rate limiting and a usage cap bound the cost, not the possibility.

## Alternatives Considered

- **DeepSeek or Qwen as the hosted LLM provider**: rejected — cheaper per token, but would require re-validating the evaluation dataset against a different model, and routes traffic through China-based infrastructure for no benefit relevant to this project's content, at a real (if soft) reputational cost.
- **Running the chat model on OCI's CPU instead of swapping to a hosted provider**: rejected — defeats the purpose; the whole reason for this ADR is that CPU-only inference is too slow for this audience.
- **A pre-recorded demo (GIF/video) instead of a live environment**: not rejected, but complementary rather than a substitute — still planned as the primary showcase in the README, precisely because it carries none of this ADR's operational risk. Recording it requires the live environment to exist first, so it doesn't remove the need for this decision.

## Open Questions Tracked for Future ADRs

- How to detect and recover from OCI reclaiming the Always Free instance for being idle (CPU/network/memory below 20% utilization for 7 days) — no automated monitoring/alerting is decided here.
- Whether manual credential provisioning needs to become semi-automated if real request volume turns out to be higher than expected.
- Ampere A1.Flex free capacity is not always available at instance-creation time in a given availability domain ("out of host capacity" errors observed during setup). No automated retry is decided here; if this remains unreliable, revisit whether a small paid shape is an acceptable fallback within the "low cost is acceptable" constraint from the original context.
