from typing import Protocol

from app.core.schemas import SourceCitation


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
