"""Voyage AI embeddings client (raw HTTP, no SDK).

Calls the Voyage REST API directly through ``httpx`` so we avoid pulling
``numpy`` (a transitive dependency of the official ``voyageai`` SDK).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal, Self

import httpx

if TYPE_CHECKING:
    from types import TracebackType

InputType = Literal["query", "document"] | None
"""Optional input-type hint accepted by the Voyage embeddings endpoint."""

DEFAULT_BASE_URL = "https://api.voyageai.com/v1"
DEFAULT_MODEL = "voyage-3"
DEFAULT_TIMEOUT = 30.0


class VoyageError(RuntimeError):
    """Raised when the Voyage API returns an error payload."""


class VoyageClient:
    """Async client for the Voyage AI embeddings endpoint.

    The client can be used as an async context manager. When the API key is
    omitted it is read from the ``VOYAGE_API_KEY`` environment variable.

    Attributes:
        model: Default embedding model name used by
            [`embed`][ragsmith.embeddings.VoyageClient.embed].

    Example:
        >>> async def main() -> list[list[float]]:
        ...     async with VoyageClient() as client:
        ...         return await client.embed(["hello world"])
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Build a new client.

        Args:
            api_key: Voyage API key. Falls back to ``VOYAGE_API_KEY`` env var.
            model: Default embedding model name.
            base_url: Voyage API base URL.
            timeout: Request timeout in seconds (ignored when ``client`` is supplied).
            client: Pre-configured ``httpx.AsyncClient`` (mainly for tests).

        Raises:
            VoyageError: If no API key is provided or found in the environment.
        """
        key = api_key or os.environ.get("VOYAGE_API_KEY")
        if not key:
            msg = "Voyage API key missing: pass api_key=... or set VOYAGE_API_KEY"
            raise VoyageError(msg)
        self._api_key = key
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the underlying HTTP client if owned."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client if it was created internally."""
        if self._owns_client:
            await self._client.aclose()

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        input_type: InputType = None,
    ) -> list[list[float]]:
        """Embed a batch of texts.

        Args:
            texts: Non-empty list of strings to embed.
            model: Optional model override (defaults to ``self.model``).
            input_type: Either ``"query"``, ``"document"`` or ``None``.

        Returns:
            List of embedding vectors aligned with the input order.

        Raises:
            ValueError: If ``texts`` is empty.
            VoyageError: If the API returns a non-2xx response.
        """
        if not texts:
            msg = "texts must be a non-empty list"
            raise ValueError(msg)

        payload: dict[str, object] = {"input": texts, "model": model or self.model}
        if input_type is not None:
            payload["input_type"] = input_type

        response = await self._client.post(
            f"{self._base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if response.status_code >= httpx.codes.BAD_REQUEST:
            msg = f"Voyage API error {response.status_code}: {response.text}"
            raise VoyageError(msg)

        data = response.json().get("data", [])
        return [item["embedding"] for item in data]
