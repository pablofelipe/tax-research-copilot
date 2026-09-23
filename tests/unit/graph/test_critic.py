import pytest

from app.core.schemas import SourceCitation, SubAnswer
from app.graph.critic import Critic, CriticError


def _citation(**overrides) -> SourceCitation:
    defaults = dict(
        source_type="primary",
        document_id="lc-214-2025",
        title="LC 214/2025",
        published_at="2025-01-16",
        content_hash="abc123",
        excerpt="Fica instituida a Contribuicao sobre Bens e Servicos (CBS).",
        url=None,
    )
    defaults.update(overrides)
    return SourceCitation(**defaults)


def _sub_answer(**overrides) -> SubAnswer:
    defaults = dict(
        sub_question="Quando o CBS entra em vigor?",
        answer="A partir de 2026, de forma escalonada.",
        citations=[_citation()],
        confidence=0.9,
    )
    defaults.update(overrides)
    return SubAnswer(**defaults)


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.last_prompt: str | None = None

    def generate(self, system_instruction: str, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


def test_verify_returns_supported_true_when_llm_confirms():
    llm = FakeLLM('{"supported": true, "reason": "o trecho sustenta a afirmacao"}')
    critic = Critic(llm)

    result = critic.verify(_sub_answer())

    assert result.supported is True
    assert result.reason == "o trecho sustenta a afirmacao"


def test_verify_returns_supported_false_when_llm_denies():
    llm = FakeLLM('{"supported": false, "reason": "o trecho nao menciona a data"}')
    critic = Critic(llm)

    result = critic.verify(_sub_answer())

    assert result.supported is False


def test_verify_raises_when_llm_response_is_not_valid_json():
    llm = FakeLLM("isso nao e json")
    critic = Critic(llm)

    with pytest.raises(CriticError):
        critic.verify(_sub_answer())


def test_verify_raises_when_llm_response_missing_supported_field():
    llm = FakeLLM('{"reason": "sem veredito"}')
    critic = Critic(llm)

    with pytest.raises(CriticError):
        critic.verify(_sub_answer())


def test_detect_conflicts_returns_empty_list_when_llm_reports_no_conflicts():
    llm = FakeLLM("[]")
    critic = Critic(llm)
    sub_answers = [_sub_answer()]

    conflicts = critic.detect_conflicts(sub_answers)

    assert conflicts == []


def test_detect_conflicts_groups_subanswers_by_indices():
    llm = FakeLLM(
        '[{"topic": "vigencia do split payment", "indices": [0, 1], '
        '"resolution_note": "Receita Federal ainda nao publicou posicao"}]'
    )
    critic = Critic(llm)
    sub_answers = [
        _sub_answer(answer="Vigora a partir de 2026."),
        _sub_answer(answer="Vigora a partir de 2027, segundo parecer de escritorio."),
    ]

    conflicts = critic.detect_conflicts(sub_answers)

    assert len(conflicts) == 1
    assert conflicts[0].topic == "vigencia do split payment"
    assert conflicts[0].positions == sub_answers
    assert conflicts[0].resolution_note == "Receita Federal ainda nao publicou posicao"


def test_detect_conflicts_raises_when_llm_response_is_not_valid_json():
    llm = FakeLLM("isso nao e json")
    critic = Critic(llm)

    with pytest.raises(CriticError):
        critic.detect_conflicts([_sub_answer()])


def test_detect_conflicts_raises_when_index_out_of_range():
    llm = FakeLLM('[{"topic": "x", "indices": [0, 5], "resolution_note": null}]')
    critic = Critic(llm)

    with pytest.raises(CriticError):
        critic.detect_conflicts([_sub_answer()])
