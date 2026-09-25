import time
from typing import Callable

import httpx


class GroqClient:
    """LLMPort adapter for Groq's OpenAI-compatible chat completions API.

    Used only in the hosted demo environment (ADR-0007) — native and
    containerized local runs keep using OllamaClient. The httpx.Client is
    injected (base_url/timeout/Authorization header are the caller's
    concern), so this adapter is testable with httpx.MockTransport, no real
    network call in unit tests.
    """

    def __init__(
        self,
        model: str,
        client: httpx.Client,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 3,
    ):
        self._model = model
        self._client = client
        self._sleep = sleep
        self._max_retries = max_retries

    def generate(self, system_instruction: str, prompt: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            # gpt-oss models spend hundreds of hidden "reasoning" tokens per
            # call by default (medium effort), which blows through the free
            # tier's per-minute token limit across a single graph run's
            # several LLM calls — "low" cuts that ~3-4x.
            "reasoning_effort": "low",
        }

        attempt = 0
        while True:
            response = self._client.post("/openai/v1/chat/completions", json=payload)
            if response.status_code == 429 and attempt < self._max_retries:
                # The free tier's per-minute token budget is tight enough
                # that a single graph run's several LLM calls can exhaust
                # it; Retry-After tells us exactly how long the window
                # takes to refill, so we wait that out instead of failing
                # a run that would otherwise have succeeded moments later.
                self._sleep(float(response.headers.get("retry-after", 5)))
                attempt += 1
                continue
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
