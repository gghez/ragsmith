"""Smoke test against the live Voyage API."""

from __future__ import annotations

import pytest

from ragsmith import VoyageClient

pytestmark = pytest.mark.integration


async def test_embed_returns_vectors(voyage_api_key: str) -> None:
    async with VoyageClient(api_key=voyage_api_key) as client:
        vectors = await client.embed(["hello world"], input_type="document")
    assert len(vectors) == 1
    assert len(vectors[0]) > 0
    assert all(isinstance(v, float) for v in vectors[0])
