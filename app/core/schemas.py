from datetime import date
from typing import Literal

from pydantic import BaseModel, field_validator


class SourceCitation(BaseModel):
    source_type: Literal["primary", "secondary"]
    document_id: str
    title: str
    published_at: date
    content_hash: str
    excerpt: str
    url: str | None = None


class SubAnswer(BaseModel):
    sub_question: str
    answer: str
    citations: list[SourceCitation]
    confidence: float

    @field_validator("citations")
    @classmethod
    def citations_must_not_be_empty(
        cls, value: list[SourceCitation]
    ) -> list[SourceCitation]:
        if not value:
            raise ValueError("a SubAnswer requires at least one citation")
        return value
