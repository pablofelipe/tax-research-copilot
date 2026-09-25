import httpx


class GroqClient:
    """LLMPort adapter for Groq's OpenAI-compatible chat completions API.

    Used only in the hosted demo environment (ADR-0007) — native and
    containerized local runs keep using OllamaClient. The httpx.Client is
    injected (base_url/timeout/Authorization header are the caller's
    concern), so this adapter is testable with httpx.MockTransport, no real
    network call in unit tests.
    """

    def __init__(self, model: str, client: httpx.Client):
        self._model = model
        self._client = client

    def generate(self, system_instruction: str, prompt: str) -> str:
        response = self._client.post(
            "/openai/v1/chat/completions",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                # gpt-oss models spend hundreds of hidden "reasoning" tokens
                # per call by default (medium effort), which blows through
                # the free tier's per-minute token limit across a single
                # graph run's several LLM calls — "low" cuts that ~3-4x.
                "reasoning_effort": "low",
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
