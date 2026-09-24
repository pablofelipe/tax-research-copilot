from datetime import date

from app.core.indexing import Indexer
from app.core.schemas import ChunkToIndex


class FakeEmbedding:
    def __init__(self):
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(len(text))]


class FakeChunkRepository:
    def __init__(self):
        self.saved: list[ChunkToIndex] = []

    def save_chunks(self, chunks: list[ChunkToIndex]) -> None:
        self.saved.extend(chunks)

    def search(self, query_embedding, top_k):
        raise NotImplementedError


def _indexer(max_chars: int = 1000) -> tuple[Indexer, FakeEmbedding, FakeChunkRepository]:
    embedding = FakeEmbedding()
    repository = FakeChunkRepository()
    return Indexer(embedding=embedding, chunk_repository=repository, max_chars=max_chars), embedding, repository


def test_index_document_embeds_and_saves_each_chunk():
    indexer, embedding, repository = _indexer(max_chars=1000)

    count = indexer.index_document(
        document_id="lc-214-2025",
        source_type="primary",
        title="LC 214/2025",
        published_at=date(2025, 1, 16),
        content_hash="abc123",
        full_text="Primeiro paragrafo.\n\nSegundo paragrafo.",
        url="https://example.org/lc214",
    )

    assert count == 1
    assert embedding.calls == ["Primeiro paragrafo.\n\nSegundo paragrafo."]
    assert repository.saved == [
        ChunkToIndex(
            document_id="lc-214-2025",
            source_type="primary",
            title="LC 214/2025",
            published_at=date(2025, 1, 16),
            content_hash="abc123",
            url="https://example.org/lc214",
            chunk_index=0,
            chunk_text="Primeiro paragrafo.\n\nSegundo paragrafo.",
            embedding=[39.0],
        )
    ]


def test_index_document_assigns_sequential_chunk_indices():
    indexer, _, repository = _indexer(max_chars=15)

    count = indexer.index_document(
        document_id="doc-1",
        source_type="secondary",
        title="Opiniao",
        published_at=date(2025, 3, 1),
        content_hash="hash1",
        full_text="AAAAAAAAAA\n\nBBBBBBBBBB\n\nCCCCCCCCCC",
        url=None,
    )

    assert count == 3
    assert [c.chunk_index for c in repository.saved] == [0, 1, 2]
    assert [c.chunk_text for c in repository.saved] == [
        "AAAAAAAAAA",
        "BBBBBBBBBB",
        "CCCCCCCCCC",
    ]


def test_index_document_with_no_chunks_saves_nothing():
    indexer, embedding, repository = _indexer()

    count = indexer.index_document(
        document_id="empty-doc",
        source_type="primary",
        title="Vazio",
        published_at=date(2025, 1, 1),
        content_hash="hash",
        full_text="   ",
        url=None,
    )

    assert count == 0
    assert embedding.calls == []
    assert repository.saved == []
