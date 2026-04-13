"""Tests for ragsmith.retriever."""

from __future__ import annotations

from typing import Any

import pytest

from ragsmith.retriever import Retriever
from ragsmith.store import Document


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str | None]] = []

    async def embed(
        self,
        texts: list[str],
        *,
        input_type: str | None = None,
    ) -> list[list[float]]:
        self.calls.append((texts, input_type))
        return [[0.1, 0.2, 0.3]]


class FakeStore:
    def __init__(self, hits: list[tuple[Document, float]]) -> None:
        self._hits = hits
        self.queries: list[tuple[list[float], int]] = []

    async def similarity_search(
        self,
        embedding: Any,
        *,
        k: int = 5,
    ) -> list[tuple[Document, float]]:
        self.queries.append((list(embedding), k))
        return self._hits


async def test_retrieve_embeds_query_and_scores_hits() -> None:
    doc = Document(content="hello", embedding=[], metadata={})
    store = FakeStore(hits=[(doc, 0.2)])
    embeddings = FakeEmbeddings()
    retriever = Retriever(embeddings, store)  # type: ignore[arg-type]

    results = await retriever.retrieve("query", k=3)

    assert embeddings.calls == [(["query"], "query")]
    assert store.queries == [([0.1, 0.2, 0.3], 3)]
    assert len(results) == 1
    assert results[0].document is doc
    assert results[0].score == pytest.approx(0.8)
