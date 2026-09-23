from typing import NamedTuple

from app.core.schemas import CONFIDENCE_THRESHOLD, DisputedPosition, SubAnswer


class EvaluationResult(NamedTuple):
    overall_confidence: float
    requires_human_review: bool


class EvaluatorError(Exception):
    """Raised when confidence cannot be aggregated."""


class Evaluator:
    def __init__(self, threshold: float = CONFIDENCE_THRESHOLD):
        self._threshold = threshold

    def evaluate(
        self,
        sub_answers: list[SubAnswer],
        disputed_positions: list[DisputedPosition],
    ) -> EvaluationResult:
        if not sub_answers:
            raise EvaluatorError("cannot aggregate confidence over an empty sub_answers list")

        overall_confidence = min(sa.confidence for sa in sub_answers)
        requires_human_review = (
            overall_confidence < self._threshold or bool(disputed_positions)
        )

        return EvaluationResult(
            overall_confidence=overall_confidence,
            requires_human_review=requires_human_review,
        )
