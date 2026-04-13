"""Generate the API reference pages for mkdocstrings."""

from pathlib import Path

import mkdocs_gen_files

SRC_ROOT = Path("src")
PACKAGE = "ragsmith"

nav = mkdocs_gen_files.Nav()

for path in sorted((SRC_ROOT / PACKAGE).rglob("*.py")):
    module_path = path.relative_to(SRC_ROOT).with_suffix("")
    doc_path = path.relative_to(SRC_ROOT).with_suffix(".md")
    full_doc_path = Path("api", doc_path)

    parts = tuple(module_path.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1].startswith("_"):
        continue

    if not parts:
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        fd.write(f"# `{'.'.join(parts)}`\n\n::: {'.'.join(parts)}\n")

    mkdocs_gen_files.set_edit_path(full_doc_path, path)

with mkdocs_gen_files.open("api/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
