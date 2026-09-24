import time
import unicodedata
from typing import Protocol

from app.core.schemas import TaxResearchResponse
from app.evaluation.schemas import CaseResult, EvaluationCase, SuiteResult


class GraphRunner(Protocol):
    """Runs the compiled graph for one query and returns its final
    response. Real implementations auto-resume a human-review pause so
    evaluation always has a response to grade; that convenience is
    evaluation-only, never a substitute for real human review in
    production.
    """

    def run(self, query: str) -> TaxResearchResponse: ...


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def run_case(runner: GraphRunner, case: EvaluationCase) -> CaseResult:
    start = time.monotonic()
    response = runner.run(case.question)
    latency_seconds = time.monotonic() - start

    citations = [c for sa in response.sub_answers for c in sa.citations]
    groundedness_ok = bool(citations) and all(
        c.document_id in case.expected_document_ids for c in citations
    )

    haystack = _normalize(
        " ".join(
            [sa.answer for sa in response.sub_answers]
            + [c.excerpt for sa in response.sub_answers for c in sa.citations]
        )
    )
    keyword_misses = [kw for kw in case.required_keywords if _normalize(kw) not in haystack]

    passed = groundedness_ok and not keyword_misses

    return CaseResult(
        case_id=case.id,
        passed=passed,
        groundedness_ok=groundedness_ok,
        keyword_misses=keyword_misses,
        latency_seconds=latency_seconds,
        requires_human_review=response.requires_human_review,
    )


def run_suite(runner: GraphRunner, cases: list[EvaluationCase]) -> SuiteResult:
    results = [run_case(runner, case) for case in cases]
    pass_rate = sum(1 for r in results if r.passed) / len(results) if results else 0.0
    average_latency = sum(r.latency_seconds for r in results) / len(results) if results else 0.0

    return SuiteResult(
        case_results=results,
        pass_rate=pass_rate,
        average_latency_seconds=average_latency,
    )
