"""Tests for ragsmith.chunking."""

from __future__ import annotations

import pytest

from ragsmith.chunking import chunk_text


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_text("   \n\t  ") == []


def test_short_text_single_chunk() -> None:
    chunks = chunk_text("Hello world.", max_chars=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world."
    assert chunks[0].index == 0
    assert chunks[0].start == 0


def test_sentence_boundary_split() -> None:
    chunks = chunk_text("Alpha. Beta. Gamma.", max_chars=10, overlap=0)
    assert [c.text for c in chunks] == ["Alpha.", "Beta.", "Gamma."]
    assert [c.index for c in chunks] == [0, 1, 2]


def test_overlap_is_applied() -> None:
    text = "Sentence one. Sentence two."
    chunks = chunk_text(text, max_chars=15, overlap=5)
    assert len(chunks) >= 2
    assert all(c.text for c in chunks)


def test_long_sentence_is_hard_cut() -> None:
    text = "x" * 250
    chunks = chunk_text(text, max_chars=100, overlap=10)
    assert len(chunks) >= 3
    assert all(len(c.text) <= 100 for c in chunks)


def test_multiple_sentences_packed_in_single_chunk() -> None:
    chunks = chunk_text("A. B. C.", max_chars=100, overlap=0)
    assert len(chunks) == 1
    assert chunks[0].text == "A. B. C."


def test_leading_terminator_is_ignored() -> None:
    chunks = chunk_text(".  Hello world.", max_chars=100, overlap=0)
    assert len(chunks) == 1
    assert "Hello" in chunks[0].text


def test_invalid_max_chars() -> None:
    with pytest.raises(ValueError, match="max_chars"):
        chunk_text("hi", max_chars=0)


def test_invalid_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("hi", max_chars=10, overlap=10)
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("hi", max_chars=10, overlap=-1)
