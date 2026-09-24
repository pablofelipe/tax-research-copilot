import httpx


class OllamaEmbeddingClient:
    """EmbeddingPort adapter for a local Ollama server. The httpx.Client is
    injected (base_url/timeout are the caller's concern) so this adapter is
    testable with httpx.MockTransport, no real network call in unit tests.
    """

    def __init__(self, model: str, client: httpx.Client):
        self._model = model
        self._client = client

    def embed(self, text: str) -> list[float]:
        response = self._client.post(
            "/api/embed",
            json={"model": self._model, "input": text},
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]
