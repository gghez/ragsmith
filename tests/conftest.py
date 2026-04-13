"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _voyage_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")


@pytest.fixture
def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ragsmith")
