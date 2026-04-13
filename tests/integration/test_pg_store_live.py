"""End-to-end tests against a live Postgres + pgvector instance."""

from __future__ import annotations

import pytest

from ragsmith import Document

pytestmark = pytest.mark.integration


async def test_upsert_and_similarity_search(pg_store) -> None:  # noqa: ANN001
    docs = [
        Document(content="alpha", embedding=[1.0, 0.0, 0.0, 0.0]),
        Document(content="beta", embedding=[0.0, 1.0, 0.0, 0.0]),
        Document(content="gamma", embedding=[0.0, 0.0, 1.0, 0.0]),
    ]
    written = await pg_store.upsert(docs)
    assert written == 3

    results = await pg_store.similarity_search([1.0, 0.0, 0.0, 0.0], k=2)
    assert len(results) == 2
    assert results[0][0].content == "alpha"
    assert results[0][1] == pytest.approx(0.0, abs=1e-6)


async def test_upsert_is_idempotent(pg_store) -> None:  # noqa: ANN001
    doc = Document(content="hello", embedding=[0.5, 0.5, 0.5, 0.5], metadata={"v": 1})
    await pg_store.upsert([doc])
    doc.content = "hello updated"
    doc.metadata = {"v": 2}
    await pg_store.upsert([doc])

    hits = await pg_store.similarity_search([0.5, 0.5, 0.5, 0.5], k=5)
    matches = [d for d, _ in hits if d.doc_id == doc.doc_id]
    assert len(matches) == 1
    assert matches[0].content == "hello updated"
    assert matches[0].metadata == {"v": 2}
