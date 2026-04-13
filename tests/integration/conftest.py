"""Fixtures for live integration tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from ragsmith import PgVectorStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set; skipping live integration test")
    return value


@pytest.fixture
async def pg_store() -> AsyncIterator[PgVectorStore]:
    dsn = _require("DATABASE_URL")
    table = f"ragsmith_it_{uuid4().hex[:8]}"
    store = await PgVectorStore.from_dsn(dsn, table=table, dim=4)
    try:
        yield store
    finally:
        async with store._pool.acquire() as conn:
            await conn.execute(f"DROP TABLE IF EXISTS {table}")
        await store.aclose()


@pytest.fixture
def voyage_api_key() -> str:
    return _require("VOYAGE_API_KEY")
