from pydantic import BaseModel


class EvaluationCase(BaseModel):
    """A single evaluation question. `required_keywords` and
    `expected_document_ids` must be verified against the real indexed
    corpus before being added to the dataset — never fabricated, per this
    project's ban on made-up evaluation data.
    """

    id: str
    question: str
    expected_document_ids: list[str]
    required_keywords: list[str]


class CaseResult(BaseModel):
    case_id: str
    passed: bool
    groundedness_ok: bool
    keyword_misses: list[str]
    latency_seconds: float
    requires_human_review: bool
    cost_usd: float = 0.0


class SuiteResult(BaseModel):
    case_results: list[CaseResult]
    pass_rate: float
    average_latency_seconds: float
