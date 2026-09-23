import json

from app.core.ports import LLMPort, RetrievalPort
from app.core.schemas import SourceCitation, SubAnswer

_SYSTEM_INSTRUCTION = (
    "Voce responde uma sub-pergunta sobre a reforma tributaria do consumo "
    "brasileira usando apenas os trechos fornecidos. Responda com um objeto "
    'JSON {"answer": string, "confidence": numero entre 0 e 1}, sem texto '
    "adicional, sem markdown. Nunca afirme algo que os trechos nao sustentem."
)


class ResearcherError(Exception):
    """Raised when no grounded answer can be produced for a sub-question."""


class Researcher:
    def __init__(self, retrieval: RetrievalPort, llm: LLMPort):
        self._retrieval = retrieval
        self._llm = llm

    def research(self, sub_question: str) -> SubAnswer:
        citations = self._retrieval.search(sub_question)
        if not citations:
            raise ResearcherError(f"no source found for sub-question: {sub_question!r}")

        prompt = self._build_prompt(sub_question, citations)
        response = self._llm.generate(_SYSTEM_INSTRUCTION, prompt)

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ResearcherError(
                f"researcher LLM response is not valid JSON: {response!r}"
            ) from exc

        if not isinstance(parsed, dict) or "answer" not in parsed or "confidence" not in parsed:
            raise ResearcherError(
                f"researcher LLM response missing answer/confidence: {response!r}"
            )

        return SubAnswer(
            sub_question=sub_question,
            answer=parsed["answer"],
            citations=citations,
            confidence=parsed["confidence"],
        )

    @staticmethod
    def _build_prompt(sub_question: str, citations: list[SourceCitation]) -> str:
        excerpts = "\n".join(f"- [{c.document_id}] {c.excerpt}" for c in citations)
        return f"Sub-pergunta: {sub_question}\n\nTrechos:\n{excerpts}"
