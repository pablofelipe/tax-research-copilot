from datetime import datetime

from app.graph.guardrail import Guardrail


def _guardrail() -> Guardrail:
    return Guardrail(clock=lambda: datetime(2026, 1, 1))


def test_in_scope_query_about_ibs_passes():
    assert _guardrail().is_in_scope("O que e o IBS?") is True


def test_in_scope_query_about_cbs_passes():
    assert _guardrail().is_in_scope("Como funciona a CBS?") is True


def test_in_scope_query_mentioning_lc_214_passes():
    assert _guardrail().is_in_scope("O que diz a LC 214/2025 sobre split payment?") is True


def test_in_scope_match_is_case_and_accent_insensitive():
    assert _guardrail().is_in_scope("qual a aliquota de referencia?") is True


def test_out_of_scope_query_fails():
    assert _guardrail().is_in_scope("Qual a capital da Franca?") is False


def test_out_of_scope_query_about_unrelated_tax_fails():
    assert _guardrail().is_in_scope("Como funciona o imposto de renda de pessoa fisica?") is False


def test_reject_builds_an_out_of_scope_response_without_citations():
    guardrail = _guardrail()

    response = guardrail.reject("Qual a capital da Franca?")

    assert response.query == "Qual a capital da Franca?"
    assert "escopo" in response.message.lower()
    assert response.generated_at == datetime(2026, 1, 1)
