"""Text chunking utilities.

Provides a simple, dependency-free sliding-window chunker that splits text
on paragraph and sentence boundaries while honoring a maximum character size
and an overlap window.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True, slots=True)
class Chunk:
    """A contiguous slice of text produced by [`chunk_text`][ragsmith.chunking.chunk_text].

    Attributes:
        index: Zero-based position of the chunk in the source document.
        text: The chunk text content.
        start: Character offset of the chunk start inside the source text.
        end: Character offset of the chunk end (exclusive) inside the source text.
    """

    index: int
    text: str
    start: int
    end: int


def chunk_text(text: str, *, max_chars: int = 1000, overlap: int = 100) -> list[Chunk]:
    """Split ``text`` into overlapping chunks.

    The splitter prefers sentence boundaries when possible. When a single
    sentence is larger than ``max_chars`` it is hard-cut.

    Args:
        text: Source text to split.
        max_chars: Maximum number of characters per chunk.
        overlap: Number of characters to repeat between consecutive chunks.

    Returns:
        Ordered list of [`Chunk`][ragsmith.chunking.Chunk]. Empty list if ``text`` is empty.

    Raises:
        ValueError: If ``max_chars`` is not strictly positive, or if
            ``overlap`` is negative or greater than/equal to ``max_chars``.

    Example:
        >>> chunks = chunk_text("Alpha. Beta. Gamma.", max_chars=10, overlap=0)
        >>> [c.text for c in chunks]
        ['Alpha.', 'Beta.', 'Gamma.']
    """
    if max_chars <= 0:
        msg = "max_chars must be > 0"
        raise ValueError(msg)
    if overlap < 0 or overlap >= max_chars:
        msg = "overlap must be in [0, max_chars)"
        raise ValueError(msg)

    stripped = text.strip()
    if not stripped:
        return []

    sentences = _SENTENCE_SPLIT.split(stripped)
    chunks: list[Chunk] = []
    buf = ""
    buf_start = 0
    cursor = 0

    def flush(buffer: str, start: int) -> None:
        if not buffer:
            return
        chunks.append(
            Chunk(index=len(chunks), text=buffer.strip(), start=start, end=start + len(buffer)),
        )

    for sentence in sentences:
        candidate = f"{buf} {sentence}".strip() if buf else sentence
        if len(candidate) <= max_chars:
            if not buf:
                buf_start = cursor
            buf = candidate
            cursor = buf_start + len(buf)
            continue

        flush(buf, buf_start)
        tail = buf[-overlap:] if overlap and buf else ""
        cursor = (buf_start + len(buf)) - len(tail)
        buf = f"{tail} {sentence}".strip() if tail else sentence
        buf_start = cursor

        while len(buf) > max_chars:
            cut = buf[:max_chars]
            flush(cut, buf_start)
            tail = cut[-overlap:] if overlap else ""
            buf_start = buf_start + max_chars - len(tail)
            buf = (tail + buf[max_chars:]).strip()

        cursor = buf_start + len(buf)

    flush(buf, buf_start)
    return chunks
