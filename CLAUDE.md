# ragsmith — project guidelines

## Hard constraints

- **Python ≥ 3.14** only.
- **No `numpy` / `pandas` anywhere** — direct or transitive. CI fails if either appears in the resolved dependency tree. Before adding any dependency, check with `uv tree | grep -iE 'numpy|pandas'`.
- **Fully async** code path (`asyncpg`, `httpx`). No sync HTTP, no sync DB calls.
- Storage talks to **Postgres + pgvector** through `asyncpg` only — do **not** introduce the optional `pgvector` Python package (it can pull `numpy`). Vectors are serialized as `'[v1,v2,...]'::vector` literals.
- Voyage AI access goes through the **raw HTTP API** via `httpx`. Never depend on the `voyageai` SDK (transitive `numpy`).

## Tooling

- Package / env management: **`uv`** (`uv sync`, `uv run …`).
- Lint + format: **`ruff`** with `select = ["ALL"]`. Pre-commit runs `ruff check` and `ruff format --check` — **no auto-fix in the hook**.
- Tests: **`pytest`** with `pytest-asyncio` (auto mode).
- Coverage: **100% gate** enforced both locally and in CI (`--cov-fail-under=100`).
- Docstrings: **Google style** (`tool.ruff.lint.pydocstyle.convention = "google"`).

## No silent rule bypasses

Do **not** add `# noqa`, `# type: ignore`, `# pragma: no cover`, `ruff: noqa`, per-file ignores in `pyproject.toml`, or any other lint/type/coverage suppression **without first flagging it to the user and getting agreement**.

The default is to fix the underlying code so it satisfies the rule. A suppression is a last resort, used only when the rule is genuinely wrong for the case at hand. When proposing one:

- State which rule, on which line, and **why** the rule does not apply.
- Wait for the user's go-ahead before committing it.

This applies equally to relaxing global config (e.g. adding to `tool.ruff.lint.ignore`, lowering `mccabe.max-complexity`, dropping `--strict`, lowering the coverage gate). Touch the config and the user must know first.

## Documentation

- Built with **MkDocs Material** + `mkdocstrings[python]`.
- API reference is **auto-generated** through `mkdocs-gen-files` (`scripts/gen_ref_pages.py`) and navigated through `mkdocs-literate-nav` (`docs/api/SUMMARY.md`). Do not hand-edit anything under `docs/api/`.
- Build must pass `uv run mkdocs build --strict` — no warnings tolerated.

## Validating example code in docstrings

Examples written in **doctest format** (`>>> …`) are executed as part of the test suite via `pytest --doctest-modules` (configured in `pyproject.toml`, `testpaths` includes `src`).

This means:

- Every `>>> ` block in a public docstring is a real test. Keep examples minimal, deterministic, and correct — they will fail CI otherwise.
- Prefer doctest over fenced ` ```python ``` ` blocks for short illustrative snippets, so the example stays in sync with the implementation.
- For longer or async examples (which doctest can't run cleanly), use a fenced code block and add a regular test in `tests/` that exercises the same flow.

## Releases

- Tagged push (`v*`) triggers `release.yml`: `uv build` → PyPI via **OIDC Trusted Publisher** (no token stored) → GitHub Release with artifacts.
- Bump `version` in `pyproject.toml` first, commit, then tag.

## Local development

- Postgres + pgvector via `docker compose up -d` (see `docker-compose.yml`).
- Secrets in `.env` (gitignored); `.env.example` is the committed template.
