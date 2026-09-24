import json

import httpx
import pytest

from app.adapters.ollama_embedding_client import OllamaEmbeddingClient


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.local")


def test_embed_returns_the_embedding_vector_from_the_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})

    client = OllamaEmbeddingClient(model="nomic-embed-text", client=_client(handler))

    result = client.embed("texto de exemplo")

    assert result == [0.1, 0.2, 0.3]


def test_embed_sends_the_model_and_input_to_the_embed_endpoint():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"embeddings": [[0.0]]})

    client = OllamaEmbeddingClient(model="nomic-embed-text", client=_client(handler))

    client.embed("texto de exemplo")

    assert captured["path"] == "/api/embed"
    assert captured["payload"] == {"model": "nomic-embed-text", "input": "texto de exemplo"}


def test_embed_raises_on_http_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model not found"})

    client = OllamaEmbeddingClient(model="nomic-embed-text", client=_client(handler))

    with pytest.raises(httpx.HTTPStatusError):
        client.embed("texto")
