"""Smoke test for the public package surface."""

from __future__ import annotations

import ragsmith


def test_public_exports() -> None:
    expected = {
        "Chunk",
        "Document",
        "PgVectorStore",
        "RetrievedChunk",
        "Retriever",
        "VoyageClient",
        "chunk_text",
    }
    assert expected.issubset(set(ragsmith.__all__))
    assert ragsmith.__version__
