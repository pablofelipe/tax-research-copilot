import argparse
import sys
import uuid

import httpx
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command

from app.adapters.ollama_client import OllamaClient
from app.adapters.ollama_embedding_client import OllamaEmbeddingClient
from app.adapters.pgvector_chunk_repository import PgVectorChunkRepository
from app.adapters.pgvector_retrieval_adapter import PgVectorRetrievalAdapter
from app.graph.build import build_graph

DEFAULT_DATABASE_URL = "postgres://tax_research:tax_research@localhost:5432/tax_research"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "llama3.1:8b"
EMBEDDING_MODEL = "nomic-embed-text"


def _build_compiled_graph(database_url: str, ollama_url: str, checkpointer):
    ollama_http = httpx.Client(base_url=ollama_url, timeout=600.0)
    llm = OllamaClient(model=LLM_MODEL, client=ollama_http)
    embedding = OllamaEmbeddingClient(model=EMBEDDING_MODEL, client=ollama_http)

    conn = psycopg.connect(database_url, autocommit=True)
    chunk_repository = PgVectorChunkRepository(conn)
    retrieval = PgVectorRetrievalAdapter(embedding=embedding, chunk_repository=chunk_repository)

    return build_graph(llm, retrieval, checkpointer=checkpointer)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the tax research graph against real adapters (Ollama + pgvector)."
    )
    parser.add_argument("query", nargs="?", help="the research question to ask")
    parser.add_argument(
        "--resume-thread-id", help="resume a paused human-review thread by its id"
    )
    parser.add_argument(
        "--decision", default="approved", help="the human decision to resume with"
    )
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    args = parser.parse_args(argv)

    if not args.query and not args.resume_thread_id:
        parser.error("a query is required, unless --resume-thread-id is given")

    with PostgresSaver.from_conn_string(args.database_url) as checkpointer:
        checkpointer.setup()
        graph = _build_compiled_graph(args.database_url, args.ollama_url, checkpointer)

        if args.resume_thread_id:
            config = {"configurable": {"thread_id": args.resume_thread_id}}
            result = graph.invoke(Command(resume=args.decision), config=config)
        else:
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            result = graph.invoke({"query": args.query}, config=config)

            if "__interrupt__" in result:
                pause = result["__interrupt__"][0].value
                print(f"Paused for human review (thread {thread_id}):")
                print(f"  query: {pause['query']}")
                print(f"  overall_confidence: {pause['overall_confidence']}")
                print(f"  disputed_positions: {len(pause['disputed_positions'])}")
                print(
                    f"\nResume with: uv run python -m app.main "
                    f"--resume-thread-id {thread_id} --decision approved"
                )
                return 0

        print(result["response"].model_dump_json(indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(main())
