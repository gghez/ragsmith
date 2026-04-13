"""End-to-end ragsmith quickstart.

Requires:

- A running Postgres + pgvector (``docker compose up -d``).
- ``DATABASE_URL`` and ``VOYAGE_API_KEY`` in the environment (e.g. ``.env``).

Run with::

    uv run python examples/quickstart.py
"""

from __future__ import annotations

import asyncio
import os

from ragsmith import Document, PgVectorStore, Retriever, VoyageClient, chunk_text

CORPUS = """
Retrieval-augmented generation combines a search step with a generation step.
The search step finds passages relevant to a user query.
The generation step conditions a language model on those passages.
Vector databases store dense embeddings to make semantic search fast.
pgvector is a Postgres extension that adds a vector column type and indexes.
"""


async def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    async with VoyageClient() as voyage:
        store = await PgVectorStore.from_dsn(dsn, table="ragsmith_quickstart", dim=1024)
        try:
            chunks = chunk_text(CORPUS, max_chars=200, overlap=20)
            print(f"chunked into {len(chunks)} pieces")

            vectors = await voyage.embed([c.text for c in chunks], input_type="document")
            written = await store.upsert(
                Document(content=c.text, embedding=v, metadata={"chunk_index": c.index})
                for c, v in zip(chunks, vectors, strict=True)
            )
            print(f"wrote {written} documents")

            retriever = Retriever(voyage, store)
            for hit in await retriever.retrieve("what is pgvector?", k=3):
                print(f"  score={hit.score:.4f}  {hit.document.content[:80]}")
        finally:
            await store.aclose()


if __name__ == "__main__":
    asyncio.run(main())
