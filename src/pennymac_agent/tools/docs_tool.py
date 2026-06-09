"""Document tools (plain functions): list and read reference docs in knowledge/."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..config.settings import get_settings

_READABLE_SUFFIXES = {".md", ".txt", ".csv", ".json", ".sql", ".yaml", ".yml"}
_MAX_CHARS = 20_000


def list_documents(subdir: Optional[str] = None) -> str:
    """List reference documents available in the knowledge directory.

    Includes overviews, data dictionaries, runbooks, and the legacy query
    library. Use this to discover what reference material you can read with
    read_document.

    Args:
        subdir: Optional subfolder under the knowledge dir to list (e.g.
            'shared', 'data_analyst', or 'legacy_queries'). Omit to list all.
    """
    s = get_settings()
    base = s.knowledge_dir
    if subdir:
        base = base / Path(subdir).name
    if not base.exists():
        return f"No knowledge directory found at {base}."
    files = [
        p
        for p in sorted(base.rglob("*"))
        if p.is_file() and p.suffix.lower() in _READABLE_SUFFIXES
    ]
    if not files:
        return f"No readable documents found under {base}."
    rels = [str(p.relative_to(s.knowledge_dir)).replace("\\", "/") for p in files]
    return "Available documents (pass the path to read_document):\n" + "\n".join(
        f"  - {r}" for r in rels
    )


def read_document(path: str) -> str:
    """Read a reference document from the knowledge directory verbatim.

    Use for exact details (definitions, steps, query patterns) rather than
    paraphrasing. Call list_documents first if unsure of the path.

    Args:
        path: Path relative to the knowledge dir, e.g. 'shared/desk_overview.md'.
    """
    s = get_settings()
    base = s.knowledge_dir.resolve()
    target = (base / path).resolve()
    if not str(target).startswith(str(base)):
        return "Error: path escapes the knowledge directory."
    if not target.exists() or not target.is_file():
        return f"Error: document '{path}' not found."
    if target.suffix.lower() not in _READABLE_SUFFIXES:
        return f"Error: '{target.suffix}' documents are not readable as text."
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "\n...[truncated]"
    return text
