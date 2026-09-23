from collections.abc import Callable
from datetime import datetime, timezone

from app.core.schemas import CONFIDENCE_THRESHOLD, DisputedPosition, SubAnswer, TaxResearchResponse
from app.graph.evaluator import EvaluationResult


class ReportGenerator:
    """No LLM call: every field is already produced upstream (Researcher's
    synthesized text, Critic's disputed positions), so composing
    human_review_notes procedurally avoids a hallucination surface in a
    field whose only job is pointing the reviewer at data already present
    in this same response.
    """

    def __init__(self, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._clock = clock

    def generate(
        self,
        query: str,
        sub_answers: list[SubAnswer],
        disputed_positions: list[DisputedPosition],
        evaluation: EvaluationResult,
    ) -> TaxResearchResponse:
        human_review_notes = None
        if evaluation.requires_human_review:
            human_review_notes = self._build_review_notes(
                evaluation.overall_confidence, disputed_positions
            )

        return TaxResearchResponse(
            query=query,
            sub_answers=sub_answers,
            disputed_positions=disputed_positions,
            overall_confidence=evaluation.overall_confidence,
            requires_human_review=evaluation.requires_human_review,
            human_review_notes=human_review_notes,
            generated_at=self._clock(),
        )

    @staticmethod
    def _build_review_notes(
        overall_confidence: float, disputed_positions: list[DisputedPosition]
    ) -> str:
        notes: list[str] = []

        if overall_confidence < CONFIDENCE_THRESHOLD:
            notes.append(
                f"Confianca geral ({overall_confidence:.2f}) abaixo do limiar "
                f"de {CONFIDENCE_THRESHOLD}."
            )

        if disputed_positions:
            topics = ", ".join(dp.topic for dp in disputed_positions)
            notes.append(
                f"{len(disputed_positions)} posicao(oes) em disputa "
                f"encontrada(s): {topics}."
            )

        return " ".join(notes)
