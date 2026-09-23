import pytest

from app.graph.planner import Planner, PlannerError


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.last_prompt: str | None = None

    def generate(self, system_instruction: str, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


def test_plan_returns_subquestions_parsed_from_llm_response():
    llm = FakeLLM('["Quando o CBS entra em vigor?", "Qual a aliquota de referencia?"]')
    planner = Planner(llm)

    sub_questions = planner.plan("Como funciona a transicao do CBS?")

    assert sub_questions == [
        "Quando o CBS entra em vigor?",
        "Qual a aliquota de referencia?",
    ]


def test_plan_passes_the_original_query_into_the_prompt():
    llm = FakeLLM('["sub-pergunta"]')
    planner = Planner(llm)

    planner.plan("Como funciona a transicao do CBS?")

    assert "Como funciona a transicao do CBS?" in llm.last_prompt


def test_plan_raises_when_llm_response_is_not_valid_json():
    llm = FakeLLM("isso nao e json")
    planner = Planner(llm)

    with pytest.raises(PlannerError):
        planner.plan("Como funciona a transicao do CBS?")


def test_plan_raises_when_llm_returns_no_subquestions():
    llm = FakeLLM("[]")
    planner = Planner(llm)

    with pytest.raises(PlannerError):
        planner.plan("Como funciona a transicao do CBS?")
