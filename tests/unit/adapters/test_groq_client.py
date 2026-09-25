import json

import httpx
import pytest

from app.adapters.groq_client import GroqClient


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://groq.local")


def test_generate_returns_message_content_from_chat_completion():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "resposta gerada"}}]})

    groq = GroqClient(model="llama-3.1-8b-instant", client=_client(handler))

    result = groq.generate("instrucao do sistema", "prompt do usuario")

    assert result == "resposta gerada"


def test_generate_sends_system_and_user_messages_to_the_chat_completions_endpoint():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    groq = GroqClient(model="llama-3.1-8b-instant", client=_client(handler))

    groq.generate("instrucao do sistema", "prompt do usuario")

    assert captured["path"] == "/openai/v1/chat/completions"
    assert captured["payload"]["model"] == "llama-3.1-8b-instant"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"] == [
        {"role": "system", "content": "instrucao do sistema"},
        {"role": "user", "content": "prompt do usuario"},
    ]
    assert captured["payload"]["reasoning_effort"] == "low"


def test_generate_raises_on_http_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "invalid api key"})

    groq = GroqClient(model="llama-3.1-8b-instant", client=_client(handler))

    with pytest.raises(httpx.HTTPStatusError):
        groq.generate("instrucao", "prompt")


def test_generate_retries_after_a_429_and_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, headers={"retry-after": "2"}, json={"error": "rate limited"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok apos retry"}}]})

    slept: list[float] = []
    groq = GroqClient(model="llama-3.1-8b-instant", client=_client(handler), sleep=slept.append)

    result = groq.generate("instrucao", "prompt")

    assert result == "ok apos retry"
    assert calls["count"] == 2
    assert slept == [2.0]


def test_generate_raises_after_exhausting_retries_on_429():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "1"}, json={"error": "rate limited"})

    slept: list[float] = []
    groq = GroqClient(
        model="llama-3.1-8b-instant", client=_client(handler), sleep=slept.append, max_retries=2
    )

    with pytest.raises(httpx.HTTPStatusError):
        groq.generate("instrucao", "prompt")

    assert slept == [1.0, 1.0]
