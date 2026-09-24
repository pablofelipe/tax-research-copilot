from app.evaluation.dataset import load_dataset
from app.evaluation.schemas import EvaluationCase


def test_load_dataset_returns_evaluation_cases():
    cases = load_dataset()

    assert len(cases) > 0
    assert all(isinstance(c, EvaluationCase) for c in cases)


def test_load_dataset_cases_have_unique_ids():
    cases = load_dataset()

    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids))


def test_load_dataset_cases_reference_a_real_expected_document():
    cases = load_dataset()

    assert all(c.expected_document_ids for c in cases)
