from app.core.ports import ChunkRepository, EmbeddingPort
from app.core.schemas import SourceCitation


class PgVectorRetrievalAdapter:
    """RetrievalPort adapter backed by a ChunkRepository (pgvector under
    the hood). Embeds the query through the same EmbeddingPort used to
    index the corpus, so both sides share one vector space.
    """

    def __init__(self, embedding: EmbeddingPort, chunk_repository: ChunkRepository, top_k: int = 5):
        self._embedding = embedding
        self._chunk_repository = chunk_repository
        self._top_k = top_k

    def search(self, query: str) -> list[SourceCitation]:
        query_embedding = self._embedding.embed(query)
        chunks = self._chunk_repository.search(query_embedding, self._top_k)
        return [
            SourceCitation(
                source_type=chunk.source_type,
                document_id=chunk.document_id,
                title=chunk.title,
                published_at=chunk.published_at,
                content_hash=chunk.content_hash,
                excerpt=chunk.chunk_text,
                url=chunk.url,
            )
            for chunk in chunks
        ]
