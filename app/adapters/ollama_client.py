import httpx


class OllamaClient:
    """LLMPort adapter for a local Ollama server. The httpx.Client is
    injected (base_url/timeout are the caller's concern) so this adapter is
    testable with httpx.MockTransport, no real network call in unit tests.
    """

    def __init__(self, model: str, client: httpx.Client):
        self._model = model
        self._client = client

    def generate(self, system_instruction: str, prompt: str) -> str:
        response = self._client.post(
            "/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
