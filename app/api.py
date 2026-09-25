import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.core.ports import AuditRepository
from app.graph.audit import build_audit_record

_STATIC_DIR = Path(__file__).parent / "static"


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
        result = graph.invoke({"query": request.query}, config=config)

        if "__interrupt__" in result:
            pause = result["__interrupt__"][0].value
            return JSONResponse(
                status_code=202,
                content={
                    "status": "pending_human_review",
                    "thread_id": thread_id,
                    "overall_confidence": pause["overall_confidence"],
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
