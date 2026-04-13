"""Cover the asyncpg-backed branch of PgVectorStore.from_dsn via monkeypatching."""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING, Any

from ragsmith.store import PgVectorStore

if TYPE_CHECKING:
    import pytest


class _Acquire:
    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def __aenter__(self) -> Any:
        return self._conn

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _FakeConn:
    async def execute(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FakePool:
    def acquire(self) -> _Acquire:
        return _Acquire(_FakeConn())

    async def close(self) -> None:
        return None


async def _create_pool(*_a: Any, **_k: Any) -> _FakePool:
    return _FakePool()


async def test_from_dsn_uses_asyncpg(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.SimpleNamespace(create_pool=_create_pool)
    monkeypatch.setitem(sys.modules, "asyncpg", fake_module)  # type: ignore[arg-type]
    store = await PgVectorStore.from_dsn("postgresql://x", table="t", dim=2)
    assert isinstance(store, PgVectorStore)
    await store.aclose()
