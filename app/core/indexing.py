from datetime import date
from typing import Literal

from app.core.chunking import chunk_text
from app.core.ports import ChunkRepository, EmbeddingPort
from app.core.schemas import ChunkToIndex


class Indexer:
    """Chunks a source document's full text, embeds each chunk, and
    persists them through a ChunkRepository — the write side of the
    corpus that PgVectorRetrievalAdapter later reads from.
    """

    def __init__(
        self,
        embedding: EmbeddingPort,
        chunk_repository: ChunkRepository,
        max_chars: int = 1000,
    ):
        self._embedding = embedding
        self._chunk_repository = chunk_repository
        self._max_chars = max_chars

    def index_document(
        self,
        *,
        document_id: str,
        source_type: Literal["primary", "secondary"],
        title: str,
        published_at: date,
        content_hash: str,
        full_text: str,
        url: str | None,
    ) -> int:
        chunks = [
            ChunkToIndex(
                document_id=document_id,
                source_type=source_type,
                title=title,
                published_at=published_at,
                content_hash=content_hash,
                url=url,
                chunk_index=index,
                chunk_text=piece,
                embedding=self._embedding.embed(piece),
            )
            for index, piece in enumerate(chunk_text(full_text, self._max_chars))
        ]

        if chunks:
            self._chunk_repository.save_chunks(chunks)

        return len(chunks)
