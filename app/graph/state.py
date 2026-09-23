from typing import TypedDict

from app.core.schemas import DisputedPosition, SubAnswer, TaxResearchResponse


class GraphState(TypedDict, total=False):
    query: str
    sub_questions: list[str]
    sub_answers: list[SubAnswer]
    disputed_positions: list[DisputedPosition]
    overall_confidence: float
    requires_human_review: bool
    response: TaxResearchResponse
