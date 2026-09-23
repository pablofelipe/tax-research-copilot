import json

from app.core.ports import LLMPort

_SYSTEM_INSTRUCTION = (
    "You decompose a Brazilian consumption tax reform question into "
    "independent, verifiable sub-questions. Respond with a JSON array of "
    "strings only, no prose, no markdown fences."
)


class PlannerError(Exception):
    """Raised when the LLM response cannot be parsed into sub-questions."""


class Planner:
    def __init__(self, llm: LLMPort):
        self._llm = llm

    def plan(self, query: str) -> list[str]:
        prompt = f"Question: {query}"
        response = self._llm.generate(_SYSTEM_INSTRUCTION, prompt)

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise PlannerError(f"planner LLM response is not valid JSON: {response!r}") from exc

        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise PlannerError(f"planner LLM response is not a JSON array of strings: {response!r}")

        if not parsed:
            raise PlannerError("planner LLM response produced no sub-questions")

        return parsed
