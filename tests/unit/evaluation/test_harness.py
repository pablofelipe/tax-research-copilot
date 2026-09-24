from datetime import datetime, timezone

from app.core.schemas import SourceCitation, SubAnswer, TaxResearchResponse
from app.evaluation.harness import run_case, run_suite
from app.evaluation.schemas import EvaluationCase


class FakeRunner:
    def __init__(self, response: TaxResearchResponse):
        self._response = response
        self.queries: list[str] = []

    def run(self, query: str) -> TaxResearchResponse:
        self.queries.append(query)
        return self._response


def _citation(document_id: str = "lc-214-2025", excerpt: str = "trecho generico") -> SourceCitation:
    return SourceCitation(
        source_type="primary",
        document_id=document_id,
        title="LC 214/2025",
        published_at="2025-01-16",
        content_hash="abc123",
        excerpt=excerpt,
        url=None,
    )


def _response(answer: str, citations: list[SourceCitation], confidence: float = 0.9) -> TaxResearchResponse:
    return TaxResearchResponse(
        query="pergunta",
        sub_answers=[
            SubAnswer(
                sub_question="pergunta",
                answer=answer,
                citations=citations,
                confidence=confidence,
            )
        ],
        disputed_positions=[],
        overall_confidence=confidence,
        requires_human_review=confidence < 0.7,
        human_review_notes=None,
        generated_at=datetime.now(timezone.utc),
    )


def test_run_case_passes_when_grounded_and_keywords_are_found():
    response = _response(
        "O IBS e o Imposto sobre Bens e Servicos.",
        [_citation(excerpt="Fica instituido o Imposto sobre Bens e Servicos - IBS")],
    )
    case = EvaluationCase(
        id="c1",
        question="O que e o IBS?",
        expected_document_ids=["lc-214-2025"],
        required_keywords=["Imposto sobre Bens e Servicos"],
    )

    result = run_case(FakeRunner(response), case)

    assert result.passed is True
    assert result.groundedness_ok is True
    assert result.keyword_misses == []


def test_run_case_fails_groundedness_when_citation_is_outside_expected_documents():
    response = _response("resposta", [_citation(document_id="documento-nao-esperado")])
    case = EvaluationCase(
        id="c2",
        question="pergunta",
        expected_document_ids=["lc-214-2025"],
        required_keywords=[],
    )

    result = run_case(FakeRunner(response), case)

    assert result.groundedness_ok is False
    assert result.passed is False


def test_run_case_reports_missing_keywords():
    response = _response("resposta sem o termo", [_citation()])
    case = EvaluationCase(
        id="c3",
        question="pergunta",
        expected_document_ids=["lc-214-2025"],
        required_keywords=["termo ausente"],
    )

    result = run_case(FakeRunner(response), case)

    assert result.keyword_misses == ["termo ausente"]
    assert result.passed is False


def test_run_case_keyword_match_is_case_insensitive():
    response = _response("O IBS E A CBS sao tributos.", [_citation()])
    case = EvaluationCase(
        id="c4",
        question="pergunta",
        expected_document_ids=["lc-214-2025"],
        required_keywords=["ibs e a cbs"],
    )

    result = run_case(FakeRunner(response), case)

    assert result.keyword_misses == []


def test_run_suite_aggregates_pass_rate_and_average_latency():
    passing = _response("O IBS.", [_citation(excerpt="IBS aqui")])
    failing = _response("resposta", [_citation(document_id="outro-doc")])
    cases = [
        EvaluationCase(id="c1", question="q1", expected_document_ids=["lc-214-2025"], required_keywords=[]),
        EvaluationCase(id="c2", question="q2", expected_document_ids=["lc-214-2025"], required_keywords=[]),
    ]
    runner = FakeRunner(passing)

    class AlternatingRunner:
        def __init__(self):
            self._responses = iter([passing, failing])

        def run(self, query: str) -> TaxResearchResponse:
            return next(self._responses)

    suite = run_suite(AlternatingRunner(), cases)

    assert suite.pass_rate == 0.5
    assert len(suite.case_results) == 2
    assert all(r.latency_seconds >= 0 for r in suite.case_results)
