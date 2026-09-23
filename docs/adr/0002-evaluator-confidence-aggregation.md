# ADR-0002: Confidence Aggregation and Human-Review Gating in the Evaluator Node

## Status

Accepted

## Context

ADR-0001 defined the Evaluator node's responsibility — aggregate confidence across sub-answers, force a blocking pause for human review below a configured threshold — but did not specify the aggregation function itself, nor how a Critic-flagged disagreement between sources should interact with that numeric gate. Both had to be resolved to implement the node.

## Decision

### Aggregation: minimum, not mean

`overall_confidence` is the minimum of all `SubAnswer.confidence` values in the response, not their average.

A mean lets one high-confidence sub-answer mask another that barely cleared the bar — or didn't. The confidence-gating guardrail (CLAUDE.md Section 8: no low-confidence response reaches the user without explicit human review) exists to catch the weakest claim in a response, not the response's central tendency. `overall_confidence` is only as strong as its weakest verified claim.

### Disputed positions force human review regardless of confidence

`requires_human_review` is forced `True` whenever the Critic produced at least one `DisputedPosition`, even if every individual sub-answer carries high confidence on its own.

A numeric confidence score has no way to represent "two credible sources disagree" — that is a qualitatively different failure mode than "the answer is uncertain." ADR-0001 already establishes that the system never resolves a disputed position on its own (`resolution_note` carries context, never a verdict); letting a high average confidence bypass human review when a live disagreement exists would silently contradict that rule.

## Alternatives Considered

- **Mean/average aggregation**: rejected — dilutes a single weak sub-answer across an otherwise strong response, defeating the purpose of the confidence gate.
- **Leaving disputes out of the review gate**, relying only on the Report Generator's disputed-positions section to surface them to the end user: rejected — a response could then be delivered without a blocking human check even when the system explicitly found something it cannot resolve on its own, contradicting the Section 8 guardrail.

## Consequences

**Positive**

- Conservative default: no weak sub-answer and no unresolved disagreement passes through silently.
- Easy to reason about and to explain in an audit trail — the trigger for human review is never ambiguous.

**Negative**

- A single borderline sub-answer confidence score (e.g., a well-supported answer the LLM scored slightly low) can force review even when the rest of the response is solid. This may need calibration once real usage data exists — tracked as an open question with the same status as the per-question-type threshold deferral already noted in ADR-0001.
