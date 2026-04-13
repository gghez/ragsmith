"""Tests for ragsmith.store using a fake asyncpg pool."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest

from ragsmith.store import Document, PgVectorStore, _vector_literal


class FakeConnection:
    def __init__(self, log: list[tuple[str, tuple[Any, ...]]], rows: list[dict[str, Any]]) -> None:
        self._log = log
        self._rows = rows

    async def execute(self, sql: str, *args: Any) -> None:
        self._log.append(("execute", (sql, *args)))

    async def executemany(self, sql: str, rows: list[tuple[Any, ...]]) -> None:
        self._log.append(("executemany", (sql, tuple(rows))))

    async def fetch(self, _sql: str, *_args: Any) -> list[dict[str, Any]]:
        return self._rows


class _Acquire:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> FakeConnection:
        return self._conn

    async def __aexit__(self, *_exc: object) -> None:
        return None


class FakePool:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.log: list[tuple[str, tuple[Any, ...]]] = []
        self._conn = FakeConnection(self.log, rows or [])
        self.closed = False

    def acquire(self) -> _Acquire:
        return _Acquire(self._conn)

    async def close(self) -> None:
        self.closed = True


def test_vector_literal_roundtrip() -> None:
    assert _vector_literal([1.0, 2.5, -3.0]) == "[1.0,2.5,-3.0]"


def test_invalid_table_name() -> None:
    with pytest.raises(ValueError, match="unsafe table"):
        PgVectorStore(FakePool(), table="bad name;", dim=3)  # type: ignore[arg-type]


def test_invalid_dim() -> None:
    with pytest.raises(ValueError, match="dim"):
        PgVectorStore(FakePool(), table="t", dim=0)  # type: ignore[arg-type]


async def test_initialize_runs_ddl() -> None:
    pool = FakePool()
    store = PgVectorStore(pool, table="ragsmith_t", dim=4)  # type: ignore[arg-type]
    await store.initialize()
    statements = [entry[1][0] for entry in pool.log if entry[0] == "execute"]
    assert any("CREATE EXTENSION" in s for s in statements)
    assert any("CREATE TABLE" in s and "ragsmith_t" in s for s in statements)
    assert any("CREATE INDEX" in s for s in statements)


async def test_upsert_no_documents_returns_zero() -> None:
    pool = FakePool()
    store = PgVectorStore(pool, table="t", dim=2)  # type: ignore[arg-type]
    assert await store.upsert([]) == 0


async def test_upsert_writes_rows() -> None:
    pool = FakePool()
    store = PgVectorStore(pool, table="t", dim=2)  # type: ignore[arg-type]
    doc = Document(content="hi", embedding=[0.1, 0.2], metadata={"k": "v"})
    written = await store.upsert([doc])
    assert written == 1
    op, payload = pool.log[-1]
    assert op == "executemany"
    sql, rows = payload
    assert "INSERT INTO t" in sql
    assert rows[0][1] == "hi"
    assert json.loads(rows[0][2]) == {"k": "v"}


async def test_similarity_search_parses_records() -> None:
    doc_id = uuid4()
    rows = [
        {
            "id": str(doc_id),
            "content": "doc",
            "metadata": json.dumps({"a": 1}),
            "embedding": "[0.1,0.2]",
            "distance": 0.25,
        },
        {
            "id": str(uuid4()),
            "content": "doc2",
            "metadata": "",
            "embedding": "[0,0]",
            "distance": 0.5,
        },
    ]
    pool = FakePool(rows=rows)
    store = PgVectorStore(pool, table="t", dim=2)  # type: ignore[arg-type]
    results = await store.similarity_search([0.0, 1.0], k=2)
    assert len(results) == 2
    first_doc, first_dist = results[0]
    assert first_doc.doc_id == doc_id
    assert first_doc.metadata == {"a": 1}
    assert first_dist == pytest.approx(0.25)
    assert results[1][0].metadata == {}


async def test_context_manager_closes_pool() -> None:
    pool = FakePool()
    async with PgVectorStore(pool, table="t", dim=2) as store:  # type: ignore[arg-type]
        assert store is not None
    assert pool.closed
