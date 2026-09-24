from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.core.schemas import SourceCitation
from app.graph.build import build_graph


class FakeSequentialLLM:
    def __init__(self, responses: list[str]):
        self._responses = iter(responses)

    def generate(self, system_instruction: str, prompt: str) -> str:
        return next(self._responses)


class FakeRetrieval:
    def __init__(self, citation: SourceCitation):
        self._citation = citation

    def search(self, query: str) -> list[SourceCitation]:
        return [self._citation]


def _citation() -> SourceCitation:
    return SourceCitation(
        source_type="primary",
        document_id="lc-214-2025",
        title="LC 214/2025",
        published_at="2025-01-16",
        content_hash="abc123",
        excerpt="Fica instituida a Contribuicao sobre Bens e Servicos (CBS).",
        url=None,
    )


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def test_graph_produces_response_without_pausing_when_confidence_is_high():
    llm = FakeSequentialLLM(
        [
            '["Quando o CBS entra em vigor?"]',
            '{"answer": "A partir de 2026, de forma escalonada.", "confidence": 0.9}',
            "[]",
        ]
    )
    graph = build_graph(llm, FakeRetrieval(_citation()), checkpointer=InMemorySaver())

    result = graph.invoke({"query": "Quando o CBS entra em vigor?"}, config=_config("t1"))

    assert "__interrupt__" not in result
    assert result["response"].requires_human_review is False
    assert result["response"].overall_confidence == 0.9


def test_graph_pauses_for_human_review_when_confidence_is_low():
    llm = FakeSequentialLLM(
        [
            '["Quando o CBS entra em vigor?"]',
            '{"answer": "A partir de 2026, de forma escalonada.", "confidence": 0.5}',
            "[]",
        ]
    )
    graph = build_graph(llm, FakeRetrieval(_citation()), checkpointer=InMemorySaver())
    config = _config("t2")

    paused = graph.invoke({"query": "Quando o CBS entra em vigor?"}, config=config)

    assert "__interrupt__" in paused
    assert "response" not in paused

    resumed = graph.invoke(Command(resume="approved"), config=config)

    assert resumed["response"].requires_human_review is True
    assert resumed["response"].overall_confidence == 0.5


def test_graph_runs_without_a_checkpointer_when_no_pause_is_needed():
    llm = FakeSequentialLLM(
        [
            '["Quando o CBS entra em vigor?"]',
            '{"answer": "A partir de 2026.", "confidence": 0.9}',
            "[]",
        ]
    )
    graph = build_graph(llm, FakeRetrieval(_citation()))

    result = graph.invoke({"query": "Quando o CBS entra em vigor?"})

    assert result["response"].overall_confidence == 0.9


class NeverCalledLLM:
    def generate(self, system_instruction: str, prompt: str) -> str:
        raise AssertionError("LLM must not be called for an out-of-scope query")


class NeverCalledRetrieval:
    def search(self, query: str) -> list[SourceCitation]:
        raise AssertionError("retrieval must not be called for an out-of-scope query")


def test_graph_rejects_an_out_of_scope_query_without_calling_llm_or_retrieval():
    graph = build_graph(NeverCalledLLM(), NeverCalledRetrieval())

    result = graph.invoke({"query": "Qual a capital da Franca?"})

    assert result["response"].query == "Qual a capital da Franca?"
    assert "escopo" in result["response"].message.lower()
