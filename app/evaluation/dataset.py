import json
from pathlib import Path

from app.evaluation.schemas import EvaluationCase

_DEFAULT_PATH = Path(__file__).parent / "dataset.json"


def load_dataset(path: Path = _DEFAULT_PATH) -> list[EvaluationCase]:
    """Loads the versioned evaluation dataset. Every entry's
    required_keywords must be a phrase verified against the real indexed
    corpus before being added — this project bans fabricated evaluation
    data.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [EvaluationCase(**entry) for entry in raw]
