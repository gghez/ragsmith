"""Postgres + pgvector storage backed by ``asyncpg``.

We avoid the optional ``pgvector`` Python package (which can pull ``numpy``)
and instead serialize vectors as ``'[v1,v2,...]'::vector`` literals.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from types import TracebackType

    import asyncpg


@dataclass(slots=True)
class Document:
    """A chunk persisted in the vector store.

    Attributes:
        content: Raw text content.
        embedding: Embedding vector (length must match the store ``dim``).
        metadata: Arbitrary JSON-serializable metadata.
        doc_id: Stable identifier (auto-generated when omitted).
    """

    content: str
    embedding: list[float]
    metadata: dict[str, object] = field(default_factory=dict)
    doc_id: UUID = field(default_factory=uuid4)


def _vector_literal(vector: Sequence[float]) -> str:
    """Encode a vector as a pgvector text literal."""
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


class PgVectorStore:
    """Async pgvector-backed document store.

    The store creates (idempotently) a single table with an ``ivfflat`` index
    on cosine distance. Use [`from_dsn`][ragsmith.store.PgVectorStore.from_dsn]
    to obtain a fully initialized instance.
    """

    def __init__(self, pool: asyncpg.Pool, *, table: str, dim: int) -> None:
        """Build a new store bound to an existing pool.

        Args:
            pool: An ``asyncpg`` connection pool.
            table: Destination table name (validated to be a SQL identifier).
            dim: Embedding dimensionality.

        Raises:
            ValueError: If ``table`` is not a safe identifier or ``dim`` <= 0.
        """
        if not table.replace("_", "").isalnum():
            msg = f"unsafe table name: {table!r}"
            raise ValueError(msg)
        if dim <= 0:
            msg = "dim must be > 0"
            raise ValueError(msg)
        self._pool = pool
        self._table = table
        self._dim = dim

    @classmethod
    async def from_dsn(
        cls,
        dsn: str,
        *,
        table: str = "ragsmith_chunks",
        dim: int = 1024,
    ) -> Self:
        """Create a store and the underlying pool from a DSN.

        Args:
            dsn: Postgres connection string.
            table: Destination table name.
            dim: Embedding dimensionality.

        Returns:
            An initialized [`PgVectorStore`][ragsmith.store.PgVectorStore].
        """
        import asyncpg  # noqa: PLC0415

        pool = await asyncpg.create_pool(dsn=dsn)
        store = cls(pool, table=table, dim=dim)
        await store.initialize()
        return store

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the underlying pool."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying connection pool."""
        await self._pool.close()

    async def initialize(self) -> None:
        """Create the pgvector extension, table and index if missing."""
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} ("
                "  id UUID PRIMARY KEY,"
                "  content TEXT NOT NULL,"
                "  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,"
                f"  embedding vector({self._dim}) NOT NULL"
                ")",
            )
            await conn.execute(
                f"CREATE INDEX IF NOT EXISTS {self._table}_embedding_idx "
                f"ON {self._table} USING ivfflat (embedding vector_cosine_ops)",
            )

    async def upsert(self, documents: Iterable[Document]) -> int:
        """Insert or update documents.

        Args:
            documents: Documents to persist.

        Returns:
            The number of rows written.
        """
        rows = [
            (str(d.doc_id), d.content, json.dumps(d.metadata), _vector_literal(d.embedding))
            for d in documents
        ]
        if not rows:
            return 0
        async with self._pool.acquire() as conn:
            await conn.executemany(
                f"INSERT INTO {self._table} (id, content, metadata, embedding) "  # noqa: S608
                "VALUES ($1, $2, $3::jsonb, $4::vector) "
                "ON CONFLICT (id) DO UPDATE SET "
                "content = EXCLUDED.content, "
                "metadata = EXCLUDED.metadata, "
                "embedding = EXCLUDED.embedding",
                rows,
            )
        return len(rows)

    async def similarity_search(
        self,
        embedding: Sequence[float],
        *,
        k: int = 5,
    ) -> list[tuple[Document, float]]:
        """Return the ``k`` documents closest to ``embedding`` (cosine distance).

        Args:
            embedding: Query vector.
            k: Number of results.

        Returns:
            Pairs of (document, distance) sorted by ascending distance.
        """
        async with self._pool.acquire() as conn:
            records = await conn.fetch(
                f"SELECT id, content, metadata, embedding, "  # noqa: S608
                f"embedding <=> $1::vector AS distance "
                f"FROM {self._table} ORDER BY distance ASC LIMIT $2",
                _vector_literal(embedding),
                k,
            )
        results: list[tuple[Document, float]] = []
        for record in records:
            doc = Document(
                doc_id=UUID(str(record["id"])),
                content=record["content"],
                metadata=json.loads(record["metadata"]) if record["metadata"] else {},
                embedding=[],
            )
            results.append((doc, float(record["distance"])))
        return results
