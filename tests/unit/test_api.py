from datetime import date, datetime, timezone

import httpx
from fastapi.testclient import TestClient

from app.api import create_app
from app.core.schemas import SubAnswer, SourceCitation, TaxResearchResponse
from app.graph.critic import CriticError


def _response(query: str) -> TaxResearchResponse:
    return TaxResearchResponse(
        query=query,
        sub_answers=[
            SubAnswer(
                sub_question="sub pergunta",
                answer="resposta",
                citations=[
                    SourceCitation(
                        document_id="lc-214-2025",
                        source_type="primary",
                        title="LC 214/2025",
                        excerpt="trecho",
                        content_hash="abc123",
                        published_at=date(2025, 1, 16),
                    )
                ],
                confidence=0.9,
            )
        ],
        disputed_positions=[],
        overall_confidence=0.9,
        requires_human_review=False,
        generated_at=datetime.now(timezone.utc),
    )


class FakeGraph:
    def __init__(self, result: dict):
        self._result = result
        self.invoked_with: list[tuple[dict, dict]] = []

    def invoke(self, state, config):
        self.invoked_with.append((state, config))
        return self._result


class RaisingGraph:
    def __init__(self, exc: Exception):
        self._exc = exc

    def invoke(self, state, config):
        raise self._exc


class FakeAuditRepository:
    def __init__(self):
        self.recorded = []

    def record(self, entry):
        self.recorded.append(entry)


def test_ask_returns_the_structured_response_for_a_completed_run():
    response = _response("Uma pergunta sobre a reforma tributaria")
    graph = FakeGraph({"query": response.query, "response": response})
    audit = FakeAuditRepository()
    client = TestClient(create_app(graph, audit))

    result = client.post("/ask", json={"query": "Uma pergunta sobre a reforma tributaria"})

    assert result.status_code == 200
    assert result.json()["query"] == "Uma pergunta sobre a reforma tributaria"
    assert result.json()["overall_confidence"] == 0.9


def test_ask_sends_the_query_to_the_graph_with_a_fresh_thread_id():
    response = _response("pergunta")
    graph = FakeGraph({"query": response.query, "response": response})
    client = TestClient(create_app(graph, FakeAuditRepository()))

    client.post("/ask", json={"query": "pergunta"})

    state, config = graph.invoked_with[0]
    assert state == {"query": "pergunta"}
    assert "thread_id" in config["configurable"]


def test_ask_records_an_audit_entry_for_a_completed_run():
    response = _response("pergunta")
    graph = FakeGraph({"query": response.query, "response": response})
    audit = FakeAuditRepository()
    client = TestClient(create_app(graph, audit))

    client.post("/ask", json={"query": "pergunta"})

    assert len(audit.recorded) == 1


def test_ask_returns_pending_review_status_when_the_graph_pauses():
    interrupt_value = {
        "query": "pergunta sensivel",
        "sub_answers": [_response("pergunta sensivel").sub_answers[0]],
        "overall_confidence": 0.4,
        "disputed_positions": [],
    }
    graph = FakeGraph(
        {"__interrupt__": [type("Interrupt", (), {"value": interrupt_value})()]}
    )
    audit = FakeAuditRepository()
    client = TestClient(create_app(graph, audit))

    result = client.post("/ask", json={"query": "pergunta sensivel"})

    assert result.status_code == 202
    body = result.json()
    assert body["status"] == "pending_human_review"
    assert "thread_id" in body
    assert body["sub_answers"][0]["answer"] == "resposta"
    assert audit.recorded == []


def test_ask_returns_a_json_error_when_a_graph_node_raises_a_known_domain_error():
    graph = RaisingGraph(CriticError("critic LLM response is not valid JSON: '...'"))
    client = TestClient(create_app(graph, FakeAuditRepository()))

    result = client.post("/ask", json={"query": "pergunta"})

    assert result.status_code == 502
    assert result.headers["content-type"].startswith("application/json")
    assert "critic LLM response" in result.json()["detail"]


def test_ask_returns_a_json_error_when_the_llm_provider_is_rate_limited():
    request = httpx.Request("POST", "https://groq.local/openai/v1/chat/completions")
    response = httpx.Response(429, request=request)
    graph = RaisingGraph(httpx.HTTPStatusError("rate limited", request=request, response=response))
    client = TestClient(create_app(graph, FakeAuditRepository()))

    result = client.post("/ask", json={"query": "pergunta"})

    assert result.status_code == 503
    assert result.headers["content-type"].startswith("application/json")
    assert "detail" in result.json()


def test_root_serves_the_html_form():
    client = TestClient(create_app(FakeGraph({}), FakeAuditRepository()))

    result = client.get("/")

    assert result.status_code == 200
    assert "text/html" in result.headers["content-type"]
    assert "<textarea" in result.text
