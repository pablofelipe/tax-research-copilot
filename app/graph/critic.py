import json
from typing import NamedTuple

from app.core.ports import LLMPort
from app.core.schemas import DisputedPosition, SubAnswer

_VERIFY_SYSTEM_INSTRUCTION = (
    "Voce verifica se os trechos citados realmente sustentam a afirmacao "
    "feita a partir deles. Responda com um objeto JSON "
    '{"supported": boolean, "reason": string}, sem texto adicional, sem '
    "markdown."
)

_CONFLICT_SYSTEM_INSTRUCTION = (
    "Voce recebe uma lista de sub-respostas sobre a reforma tributaria do "
    "consumo brasileira, cada uma identificada por indice. Identifique "
    "grupos de sub-respostas que discordam sobre o mesmo topico (ex.: texto "
    "de lei vs. parecer de escritorio). Responda com um array JSON de "
    'objetos {"topic": string, "indices": [int, ...], "resolution_note": '
    "string ou null}, sem texto adicional, sem markdown. Se nao houver "
    "conflito, responda []."
)


class VerificationResult(NamedTuple):
    supported: bool
    reason: str


class CriticError(Exception):
    """Raised when the LLM response cannot be parsed into a verdict."""


class Critic:
    def __init__(self, llm: LLMPort):
        self._llm = llm

    def verify(self, sub_answer: SubAnswer) -> VerificationResult:
        prompt = self._build_verify_prompt(sub_answer)
        response = self._llm.generate(_VERIFY_SYSTEM_INSTRUCTION, prompt)

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise CriticError(f"critic LLM response is not valid JSON: {response!r}") from exc

        if not isinstance(parsed, dict) or "supported" not in parsed or "reason" not in parsed:
            raise CriticError(
                f"critic LLM response missing supported/reason: {response!r}"
            )

        return VerificationResult(supported=parsed["supported"], reason=parsed["reason"])

    def detect_conflicts(self, sub_answers: list[SubAnswer]) -> list[DisputedPosition]:
        prompt = self._build_conflict_prompt(sub_answers)
        response = self._llm.generate(_CONFLICT_SYSTEM_INSTRUCTION, prompt)

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise CriticError(f"critic LLM response is not valid JSON: {response!r}") from exc

        if not isinstance(parsed, list):
            raise CriticError(f"critic LLM response is not a JSON array: {response!r}")

        disputes: list[DisputedPosition] = []
        for group in parsed:
            if not isinstance(group, dict) or "topic" not in group or "indices" not in group:
                raise CriticError(f"critic LLM conflict group is malformed: {group!r}")

            indices = group["indices"]
            if any(not isinstance(i, int) or i < 0 or i >= len(sub_answers) for i in indices):
                raise CriticError(f"critic LLM conflict group has out-of-range indices: {group!r}")

            disputes.append(
                DisputedPosition(
                    topic=group["topic"],
                    positions=[sub_answers[i] for i in indices],
                    resolution_note=group.get("resolution_note"),
                )
            )

        return disputes

    @staticmethod
    def _build_verify_prompt(sub_answer: SubAnswer) -> str:
        excerpts = "\n".join(
            f"- [{c.document_id}] {c.excerpt}" for c in sub_answer.citations
        )
        return (
            f"Afirmacao: {sub_answer.answer}\n\nTrechos citados:\n{excerpts}"
        )

    @staticmethod
    def _build_conflict_prompt(sub_answers: list[SubAnswer]) -> str:
        entries = "\n".join(
            f"{i}. [{sa.sub_question}] {sa.answer}" for i, sa in enumerate(sub_answers)
        )
        return f"Sub-respostas:\n{entries}"
