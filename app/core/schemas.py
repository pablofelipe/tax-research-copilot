from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CONFIDENCE_THRESHOLD = 0.7


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
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("citations")
    @classmethod
    def citations_must_not_be_empty(
        cls, value: list[SourceCitation]
    ) -> list[SourceCitation]:
        if not value:
            raise ValueError("a SubAnswer requires at least one citation")
        return value


class DisputedPosition(BaseModel):
    topic: str
    positions: list[SubAnswer]
    resolution_note: str | None = None

    @field_validator("positions")
    @classmethod
    def positions_must_conflict(cls, value: list[SubAnswer]) -> list[SubAnswer]:
        if len(value) < 2:
            raise ValueError(
                "a DisputedPosition requires at least two conflicting positions"
            )
        return value


class TaxResearchResponse(BaseModel):
    query: str
    sub_answers: list[SubAnswer]
    disputed_positions: list[DisputedPosition]
    overall_confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    human_review_notes: str | None = None
    generated_at: datetime

    @field_validator("sub_answers")
    @classmethod
    def sub_answers_must_not_be_empty(cls, value: list[SubAnswer]) -> list[SubAnswer]:
        if not value:
            raise ValueError("a TaxResearchResponse requires at least one sub-answer")
        return value

    @model_validator(mode="after")
    def low_confidence_forces_human_review(self) -> "TaxResearchResponse":
        if self.overall_confidence < CONFIDENCE_THRESHOLD and not self.requires_human_review:
            raise ValueError(
                f"overall_confidence below {CONFIDENCE_THRESHOLD} requires "
                "requires_human_review=True"
            )
        return self
