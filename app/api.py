import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.core.ports import AuditRepository
from app.graph.audit import build_audit_record
from app.graph.critic import CriticError
from app.graph.evaluator import EvaluatorError
from app.graph.planner import PlannerError
from app.graph.researcher import ResearcherError

_STATIC_DIR = Path(__file__).parent / "static"
_DOMAIN_ERRORS = (PlannerError, ResearcherError, CriticError, EvaluatorError)


class CompiledGraph(Protocol):
    """The subset of LangGraph's compiled-graph interface this module
    depends on, so it can be exercised with a fake in unit tests instead of
    a real checkpointer/database connection.
    """

    def invoke(self, state: dict, config: dict) -> dict: ...


class AskRequest(BaseModel):
    query: str


def create_app(graph: CompiledGraph, audit_repository: AuditRepository) -> FastAPI:
    """Composition-layer HTTP entry point for the hosted demo (ADR-0007).

    Access control (HTTP Basic Auth, HTTPS, rate limiting) is handled by the
    reverse proxy in front of this app, not here — this endpoint only wraps
    the existing graph, the same way app/main.py does for the CLI.
    """
    app = FastAPI(title="Tax Research Copilot")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (_STATIC_DIR / "index.html").read_text(encoding="utf-8")

    @app.post("/ask")
    def ask(request: AskRequest):
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        try:
            result = graph.invoke({"query": request.query}, config=config)
        except _DOMAIN_ERRORS as exc:
            # These are the graph's own documented failure modes (an LLM
            # producing an ungrounded or malformed response — see ADR-0001's
            # Known Limitations), not application bugs: surfaced as a clean
            # JSON error instead of FastAPI's default plain-text 500 page,
            # which the demo page can't parse.
            return JSONResponse(status_code=502, content={"detail": str(exc)})
        except httpx.HTTPStatusError as exc:
            # GroqClient already retries a 429 against Retry-After; this is
            # what escapes after exhausting those retries, or any other
            # upstream LLM provider failure — same "don't leak a plain-text
            # 500" reasoning as above.
            return JSONResponse(
                status_code=503,
                content={"detail": f"the LLM provider is unavailable: {exc}"},
            )

        if "__interrupt__" in result:
            pause = result["__interrupt__"][0].value
            return JSONResponse(
                status_code=202,
                content={
                    "status": "pending_human_review",
                    "thread_id": thread_id,
                    "overall_confidence": pause["overall_confidence"],
                    "sub_answers": [sa.model_dump(mode="json") for sa in pause["sub_answers"]],
                },
            )

        response = result["response"]
        audit_repository.record(
            build_audit_record(
                thread_id=thread_id,
                query=result.get("query", request.query),
                response=response,
                human_decision=None,
                clock=lambda: datetime.now(timezone.utc),
            )
        )
        return response

    return app
