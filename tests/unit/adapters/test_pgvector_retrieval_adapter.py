from datetime import date

from app.adapters.pgvector_retrieval_adapter import PgVectorRetrievalAdapter
from app.core.schemas import ChunkSearchResult, SourceCitation


class FakeEmbedding:
    def __init__(self, vector: list[float]):
        self._vector = vector
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return self._vector


class FakeChunkRepository:
    def __init__(self, results: list[ChunkSearchResult]):
        self._results = results
        self.search_calls: list[tuple[list[float], int]] = []

    def save_chunks(self, chunks):
        raise NotImplementedError

    def search(self, query_embedding: list[float], top_k: int) -> list[ChunkSearchResult]:
        self.search_calls.append((query_embedding, top_k))
        return self._results


def test_search_embeds_the_query_and_returns_citations_from_matching_chunks():
    chunk = ChunkSearchResult(
        document_id="lc-214-2025",
        source_type="primary",
        title="LC 214/2025",
        published_at=date(2025, 1, 16),
        content_hash="abc123",
        url="https://example.org/lc214",
        chunk_text="texto do trecho encontrado",
    )
    embedding = FakeEmbedding([0.1, 0.2])
    repository = FakeChunkRepository(results=[chunk])
    adapter = PgVectorRetrievalAdapter(embedding=embedding, chunk_repository=repository, top_k=5)

    result = adapter.search("qual a aliquota da CBS?")

    assert embedding.calls == ["qual a aliquota da CBS?"]
    assert repository.search_calls == [([0.1, 0.2], 5)]
    assert result == [
        SourceCitation(
            source_type="primary",
            document_id="lc-214-2025",
            title="LC 214/2025",
            published_at=date(2025, 1, 16),
            content_hash="abc123",
            excerpt="texto do trecho encontrado",
            url="https://example.org/lc214",
        )
    ]


def test_search_returns_empty_list_when_no_chunks_match():
    adapter = PgVectorRetrievalAdapter(
        embedding=FakeEmbedding([0.0]),
        chunk_repository=FakeChunkRepository(results=[]),
    )

    result = adapter.search("pergunta sem fonte no corpus")

    assert result == []
