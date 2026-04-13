"""High-level retriever wiring an embeddings client and a vector store."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ragsmith.embeddings import VoyageClient
    from ragsmith.store import Document, PgVectorStore


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A single retrieval result.

    Attributes:
        document: The matched document.
        score: Cosine similarity score in ``[0, 1]`` (``1 - distance``).
    """

    document: Document
    score: float


class Retriever:
    """Embed a query and look it up in a [`PgVectorStore`][ragsmith.store.PgVectorStore]."""

    def __init__(self, embeddings: VoyageClient, store: PgVectorStore) -> None:
        """Build a retriever.

        Args:
            embeddings: The Voyage client used for query embeddings.
            store: The destination vector store.
        """
        self._embeddings = embeddings
        self._store = store

    async def retrieve(self, query: str, *, k: int = 5) -> list[RetrievedChunk]:
        """Embed ``query`` and return the top-``k`` similar documents.

        Args:
            query: User query.
            k: Maximum number of documents to return.

        Returns:
            Ordered list of [`RetrievedChunk`][ragsmith.retriever.RetrievedChunk].
        """
        vectors = await self._embeddings.embed([query], input_type="query")
        hits = await self._store.similarity_search(vectors[0], k=k)
        return [RetrievedChunk(document=doc, score=1.0 - distance) for doc, distance in hits]
