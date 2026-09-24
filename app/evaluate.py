import argparse
import sys

import httpx
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

from app.adapters.ollama_client import OllamaClient
from app.adapters.ollama_embedding_client import OllamaEmbeddingClient
from app.adapters.pgvector_chunk_repository import PgVectorChunkRepository
from app.adapters.pgvector_retrieval_adapter import PgVectorRetrievalAdapter
from app.evaluation.dataset import load_dataset
from app.evaluation.harness import run_suite
from app.evaluation.langgraph_runner import LangGraphRunner
from app.graph.build import build_graph
from app.main import DEFAULT_DATABASE_URL, DEFAULT_OLLAMA_URL, EMBEDDING_MODEL, LLM_MODEL


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the evaluation dataset against the real graph (Ollama + pgvector)."
    )
    parser.add_argument("--database-url", default=DEFAULT_DATABASE_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument(
        "--limit", type=int, default=None, help="only run the first N cases (for a quick smoke run)"
    )
    args = parser.parse_args(argv)

    cases = load_dataset()
    if args.limit is not None:
        cases = cases[: args.limit]

    ollama_http = httpx.Client(base_url=args.ollama_url, timeout=600.0)
    llm = OllamaClient(model=LLM_MODEL, client=ollama_http)
    embedding = OllamaEmbeddingClient(model=EMBEDDING_MODEL, client=ollama_http)

    conn = psycopg.connect(args.database_url, autocommit=True)
    chunk_repository = PgVectorChunkRepository(conn)
    retrieval = PgVectorRetrievalAdapter(embedding=embedding, chunk_repository=chunk_repository)

    with PostgresSaver.from_conn_string(args.database_url) as checkpointer:
        checkpointer.setup()
        graph = build_graph(llm, retrieval, checkpointer=checkpointer)
        runner = LangGraphRunner(graph)

        suite = run_suite(runner, cases)

    for result in suite.case_results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id} "
            f"(grounded={result.groundedness_ok}, "
            f"missing={result.keyword_misses}, "
            f"human_review={result.requires_human_review}, "
            f"latency={result.latency_seconds:.1f}s)"
        )

    print(
        f"\n{len(suite.case_results)} cases, "
        f"pass_rate={suite.pass_rate:.0%}, "
        f"avg_latency={suite.average_latency_seconds:.1f}s"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
