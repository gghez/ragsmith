# ragsmith

[![CI](https://github.com/gghez/ragsmith/actions/workflows/ci.yml/badge.svg)](https://github.com/gghez/ragsmith/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://gghez.github.io/ragsmith/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Async RAG toolkit on top of **Postgres + pgvector** and **Voyage AI**, with
zero direct or indirect `numpy` / `pandas` dependency.

## Highlights

- 100% async (`asyncpg`, `httpx`).
- Voyage embeddings via the raw HTTP API (no SDK, no `numpy`).
- pgvector storage with cosine similarity search.
- Strict tooling: `ruff` (all rules), `pytest`, 100% coverage in CI.
- Python 3.14+.

## Install

```bash
uv sync
```

## Local pgvector database

A `docker-compose.yml` is provided for local development and integration
testing:

```bash
docker compose up -d           # start Postgres + pgvector on localhost:5432
docker compose down -v         # stop and wipe the volume
```

Connection string (also written in `.env.example`):

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ragsmith
```

## Usage

```python
import asyncio
import os

from ragsmith import PgVectorStore, VoyageClient, Retriever, Document, chunk_text


async def main() -> None:
    async with VoyageClient() as voyage:
        store = await PgVectorStore.from_dsn(os.environ["DATABASE_URL"], dim=1024)
        try:
            chunks = chunk_text("Long document text...", max_chars=500)
            vectors = await voyage.embed([c.text for c in chunks], input_type="document")
            await store.upsert(
                Document(content=c.text, embedding=v)
                for c, v in zip(chunks, vectors, strict=True)
            )

            retriever = Retriever(voyage, store)
            for hit in await retriever.retrieve("what is rag?", k=3):
                print(hit.score, hit.document.content)
        finally:
            await store.aclose()


asyncio.run(main())
```

## Documentation

Full API reference: <https://gghez.github.io/ragsmith/>

## Releasing

Releases are fully automated through GitHub Actions and PyPI Trusted
Publishing (OIDC, no API token stored).

1. Bump `version` in `pyproject.toml` and commit (e.g. `chore: bump to 0.2.0`).
2. Tag and push:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. The `Release` workflow runs `uv build`, publishes the sdist + wheel to
   PyPI and creates a matching GitHub Release with the artifacts attached.

One-time PyPI setup: register the project on PyPI as a
[Trusted Publisher](https://docs.pypi.org/trusted-publishers/) pointing to
`gghez/ragsmith`, workflow `release.yml`, environment `pypi`.

## License

MIT
