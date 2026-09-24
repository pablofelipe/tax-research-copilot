from typing import Protocol

from app.core.schemas import ChunkSearchResult, ChunkToIndex, SourceCitation


class RetrievalPort(Protocol):
    """Searches the indexed corpus for excerpts relevant to a sub-question.

    Implementations must never fabricate a result: an empty return means
    "not found", never a paraphrase without a backing source.
    """

    def search(self, query: str) -> list[SourceCitation]: ...


class LLMPort(Protocol):
    """Generic text-generation capability, deliberately provider-agnostic.

    No concrete LLM provider has been chosen yet for this project; nodes
    depend on this Protocol, never on a specific vendor SDK.
    """

    def generate(self, system_instruction: str, prompt: str) -> str: ...


class EmbeddingPort(Protocol):
    """Generic text-embedding capability, deliberately provider-agnostic.

    Used both when indexing the corpus (embedding chunks) and at query
    time (embedding a search query), so both sides stay in the same
    vector space regardless of which concrete model is behind this port.
    """

    def embed(self, text: str) -> list[float]: ...


class ChunkRepository(Protocol):
    """Storage for embedded document chunks, backing both indexing (write)
    and retrieval (similarity search / read).
    """

    def save_chunks(self, chunks: list[ChunkToIndex]) -> None: ...

    def search(self, query_embedding: list[float], top_k: int) -> list[ChunkSearchResult]: ...
