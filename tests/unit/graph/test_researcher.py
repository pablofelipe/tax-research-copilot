import pytest
from pydantic import ValidationError

from app.core.schemas import SourceCitation
from app.graph.researcher import Researcher, ResearcherError


def _citation(**overrides) -> SourceCitation:
    defaults = dict(
        source_type="primary",
        document_id="lc-214-2025",
        title="LC 214/2025",
        published_at="2025-01-16",
        content_hash="abc123",
        excerpt="Fica instituida a Contribuicao sobre Bens e Servicos (CBS).",
        url=None,
    )
    defaults.update(overrides)
    return SourceCitation(**defaults)


class FakeRetrieval:
    def __init__(self, results: list[SourceCitation]):
        self.results = results
        self.last_query: str | None = None

    def search(self, query: str) -> list[SourceCitation]:
        self.last_query = query
        return self.results


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = 0
        self.last_prompt: str | None = None

    def generate(self, system_instruction: str, prompt: str) -> str:
        self.calls += 1
        self.last_prompt = prompt
        return self.response


def test_research_raises_when_retrieval_finds_no_citations():
    retrieval = FakeRetrieval([])
    llm = FakeLLM('{"answer": "should not be used", "confidence": 0.9}')
    researcher = Researcher(retrieval, llm)

    with pytest.raises(ResearcherError):
        researcher.research("Quando o CBS entra em vigor?")

    assert llm.calls == 0


def test_research_returns_subanswer_grounded_in_citations():
    citation = _citation()
    retrieval = FakeRetrieval([citation])
    llm = FakeLLM('{"answer": "A partir de 2026, de forma escalonada.", "confidence": 0.85}')
    researcher = Researcher(retrieval, llm)

    sub_answer = researcher.research("Quando o CBS entra em vigor?")

    assert sub_answer.answer == "A partir de 2026, de forma escalonada."
    assert sub_answer.confidence == 0.85
    assert sub_answer.citations == [citation]


def test_research_includes_excerpt_in_the_prompt():
    citation = _citation(excerpt="Trecho especifico da norma.")
    retrieval = FakeRetrieval([citation])
    llm = FakeLLM('{"answer": "resposta", "confidence": 0.8}')
    researcher = Researcher(retrieval, llm)

    researcher.research("Quando o CBS entra em vigor?")

    assert "Trecho especifico da norma." in llm.last_prompt


def test_research_raises_when_llm_response_is_not_valid_json():
    retrieval = FakeRetrieval([_citation()])
    llm = FakeLLM("isso nao e json")
    researcher = Researcher(retrieval, llm)

    with pytest.raises(ResearcherError):
        researcher.research("Quando o CBS entra em vigor?")


def test_research_raises_when_llm_response_missing_required_fields():
    retrieval = FakeRetrieval([_citation()])
    llm = FakeLLM('{"answer": "resposta sem confianca"}')
    researcher = Researcher(retrieval, llm)

    with pytest.raises(ResearcherError):
        researcher.research("Quando o CBS entra em vigor?")


def test_research_propagates_schema_validation_when_confidence_out_of_bounds():
    retrieval = FakeRetrieval([_citation()])
    llm = FakeLLM('{"answer": "resposta", "confidence": 1.5}')
    researcher = Researcher(retrieval, llm)

    with pytest.raises(ValidationError):
        researcher.research("Quando o CBS entra em vigor?")
