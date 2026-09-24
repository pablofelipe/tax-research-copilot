import unicodedata
from collections.abc import Callable
from datetime import datetime, timezone

from app.core.schemas import OutOfScopeResponse

# Drawn directly from this project's declared domain (the Brazilian
# consumption tax reform: EC 132/2023, LC 214/2025 and its infralegal
# follow-on). Deliberately keyword-based, not an LLM call — the
# guardrail's whole point is to reject an out-of-scope query before
# spending any LLM or retrieval call on it.
_IN_SCOPE_TERMS = [
    "ibs",
    "cbs",
    "imposto seletivo",
    "reforma tributaria",
    "ec 132",
    "emenda constitucional 132",
    "lc 214",
    "lei complementar 214",
    "split payment",
    "comite gestor",
    "cbs e ibs",
    "aliquota de referencia",
    "cesta basica nacional",
    "imposto sobre bens e servicos",
    "contribuicao sobre bens e servicos",
    "transicao tributaria",
    "tributo sobre consumo",
    "tributos de consumo",
]


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


class Guardrail:
    """Rejects a query before any retrieval or LLM call when it falls
    outside this project's declared domain — consumption tax reform,
    not tax law in general.
    """

    def __init__(self, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._clock = clock

    def is_in_scope(self, query: str) -> bool:
        normalized = _normalize(query)
        return any(term in normalized for term in _IN_SCOPE_TERMS)

    def reject(self, query: str) -> OutOfScopeResponse:
        return OutOfScopeResponse(
            query=query,
            message=(
                "Esta pergunta esta fora do escopo deste sistema, que cobre apenas "
                "a reforma tributaria brasileira sobre o consumo (EC 132/2023, "
                "LC 214/2025 e regulamentacao posterior)."
            ),
            generated_at=self._clock(),
        )
