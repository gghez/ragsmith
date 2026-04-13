"""Tests for ragsmith.embeddings."""

from __future__ import annotations

import httpx
import pytest

from ragsmith.embeddings import VoyageClient, VoyageError


async def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    with pytest.raises(VoyageError, match="Voyage API key missing"):
        VoyageClient()


async def test_embed_empty_texts_raises() -> None:
    transport = httpx.MockTransport(lambda _r: httpx.Response(200, json={"data": []}))
    async with httpx.AsyncClient(transport=transport) as http:
        client = VoyageClient(api_key="k", client=http)
        with pytest.raises(ValueError, match="non-empty"):
            await client.embed([])


async def test_embed_returns_vectors_and_uses_input_type() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = VoyageClient(api_key="secret", client=http, model="voyage-3")
        out = await client.embed(["a", "b"], input_type="query")

    assert out == [[0.1, 0.2], [0.3, 0.4]]
    assert seen["url"].endswith("/embeddings")
    assert seen["auth"] == "Bearer secret"
    assert "input_type" in seen["body"]


async def test_embed_error_response_raises() -> None:
    transport = httpx.MockTransport(lambda _r: httpx.Response(500, text="boom"))
    async with httpx.AsyncClient(transport=transport) as http:
        client = VoyageClient(api_key="k", client=http)
        with pytest.raises(VoyageError, match="500"):
            await client.embed(["x"])


async def test_context_manager_closes_owned_client() -> None:
    async with VoyageClient(api_key="k") as client:
        assert client.model


async def test_external_client_not_closed() -> None:
    transport = httpx.MockTransport(lambda _r: httpx.Response(200, json={"data": []}))
    http = httpx.AsyncClient(transport=transport)
    client = VoyageClient(api_key="k", client=http)
    await client.aclose()
    assert not http.is_closed
    await http.aclose()
