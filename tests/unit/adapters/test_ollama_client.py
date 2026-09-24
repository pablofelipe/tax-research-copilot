import json

import httpx
import pytest

from app.adapters.ollama_client import OllamaClient


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.local")


def test_generate_returns_message_content_from_chat_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "resposta gerada"}})

    ollama = OllamaClient(model="llama3.1:8b", client=_client(handler))

    result = ollama.generate("instrucao do sistema", "prompt do usuario")

    assert result == "resposta gerada"


def test_generate_sends_system_and_user_messages_to_the_chat_endpoint():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "ok"}})

    ollama = OllamaClient(model="llama3.1:8b", client=_client(handler))

    ollama.generate("instrucao do sistema", "prompt do usuario")

    assert captured["path"] == "/api/chat"
    assert captured["payload"]["model"] == "llama3.1:8b"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"] == [
        {"role": "system", "content": "instrucao do sistema"},
        {"role": "user", "content": "prompt do usuario"},
    ]


def test_generate_raises_on_http_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model not found"})

    ollama = OllamaClient(model="llama3.1:8b", client=_client(handler))

    with pytest.raises(httpx.HTTPStatusError):
        ollama.generate("instrucao", "prompt")
