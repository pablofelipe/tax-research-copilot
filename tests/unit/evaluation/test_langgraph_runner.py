from langgraph.checkpoint.memory import InMemorySaver

from app.core.schemas import SourceCitation
from app.evaluation.langgraph_runner import LangGraphRunner
from app.graph.build import build_graph


class FakeSequentialLLM:
    def __init__(self, responses: list[str]):
        self._responses = iter(responses)

    def generate(self, system_instruction: str, prompt: str) -> str:
        return next(self._responses)


class FakeRetrieval:
    def search(self, query: str) -> list[SourceCitation]:
        return [
            SourceCitation(
                source_type="primary",
                document_id="lc-214-2025",
                title="LC 214/2025",
                published_at="2025-01-16",
                content_hash="abc123",
                excerpt="Fica instituida a Contribuicao sobre Bens e Servicos (CBS).",
                url=None,
            )
        ]


def test_run_returns_the_response_when_no_pause_is_needed():
    llm = FakeSequentialLLM(
        [
            '["Quando o CBS entra em vigor?"]',
            '{"answer": "A partir de 2026.", "confidence": 0.9}',
            "[]",
        ]
    )
    graph = build_graph(llm, FakeRetrieval(), checkpointer=InMemorySaver())
    runner = LangGraphRunner(graph)

    response = runner.run("Quando o CBS entra em vigor?")

    assert response.requires_human_review is False
    assert response.overall_confidence == 0.9


def test_run_auto_resumes_when_paused_for_human_review():
    llm = FakeSequentialLLM(
        [
            '["Quando o CBS entra em vigor?"]',
            '{"answer": "A partir de 2026.", "confidence": 0.5}',
            "[]",
        ]
    )
    graph = build_graph(llm, FakeRetrieval(), checkpointer=InMemorySaver())
    runner = LangGraphRunner(graph)

    response = runner.run("Quando o CBS entra em vigor?")

    assert response.requires_human_review is True
    assert response.overall_confidence == 0.5
