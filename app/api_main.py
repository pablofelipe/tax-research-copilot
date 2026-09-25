import os

import httpx
import psycopg
import uvicorn
from langgraph.checkpoint.postgres import PostgresSaver

from app.adapters.groq_client import GroqClient
from app.adapters.ollama_client import OllamaClient
from app.adapters.ollama_embedding_client import OllamaEmbeddingClient
from app.adapters.pgvector_chunk_repository import PgVectorChunkRepository
from app.adapters.pgvector_retrieval_adapter import PgVectorRetrievalAdapter
from app.adapters.postgres_audit_repository import PostgresAuditRepository
from app.api import create_app
from app.graph.build import build_graph
from app.observability.tracing import DEFAULT_OTLP_ENDPOINT, configure_tracing

DEFAULT_DATABASE_URL = "postgres://tax_research:tax_research@localhost:5432/tax_research"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_GROQ_URL = "https://api.groq.com"
LLM_MODEL = "llama3.1:8b"
GROQ_MODEL = "llama-3.1-8b-instant"
EMBEDDING_MODEL = "nomic-embed-text"


def _build_llm():
    """Selects the LLM adapter for this process via LLM_PROVIDER (ADR-0007).

    Defaults to Ollama, matching every other entry point in this project;
    the hosted demo sets LLM_PROVIDER=groq explicitly rather than this
    module guessing based on which environment variables happen to be set.
    """
    provider = os.environ.get("LLM_PROVIDER", "ollama")
    if provider == "groq":
        api_key = os.environ["GROQ_API_KEY"]
        groq_http = httpx.Client(
            base_url=os.environ.get("GROQ_URL", DEFAULT_GROQ_URL),
            timeout=60.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        return GroqClient(model=os.environ.get("GROQ_MODEL", GROQ_MODEL), client=groq_http)
    if provider == "ollama":
        ollama_http = httpx.Client(
            base_url=os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL), timeout=600.0
        )
        return OllamaClient(model=LLM_MODEL, client=ollama_http)
    raise ValueError(f"unknown LLM_PROVIDER: {provider!r}")


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    ollama_url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    otlp_endpoint = os.environ.get("OTLP_ENDPOINT", DEFAULT_OTLP_ENDPOINT)

    configure_tracing("tax-research-copilot-api", otlp_endpoint)

    llm = _build_llm()
    embedding_http = httpx.Client(base_url=ollama_url, timeout=600.0)
    embedding = OllamaEmbeddingClient(model=EMBEDDING_MODEL, client=embedding_http)

    conn = psycopg.connect(database_url, autocommit=True)
    chunk_repository = PgVectorChunkRepository(conn)
    retrieval = PgVectorRetrievalAdapter(embedding=embedding, chunk_repository=chunk_repository)
    audit_repository = PostgresAuditRepository(psycopg.connect(database_url, autocommit=True))

    with PostgresSaver.from_conn_string(database_url) as checkpointer:
        checkpointer.setup()
        graph = build_graph(llm, retrieval, checkpointer=checkpointer)
        app = create_app(graph, audit_repository)
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
