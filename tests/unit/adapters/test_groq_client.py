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
