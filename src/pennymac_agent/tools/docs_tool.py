"""CrewAI tools for deterministic access to reference documents on disk.

These read from the knowledge directory directly (no embeddings), complementing
the RAG knowledge sources. Useful when an agent wants to read a specific
reference doc verbatim.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config.settings import Settings, get_settings

_READABLE_SUFFIXES = {".md", ".txt", ".csv", ".json", ".sql", ".yaml", ".yml"}
_MAX_CHARS = 20_000


class ListDocumentsInput(BaseModel):
    subdir: Optional[str] = Field(
        None,
        description=(
            "Optional subfolder under the knowledge dir to list (e.g. 'shared' "
            "or a specialist key). Omit to list everything."
        ),
    )


class ListDocumentsTool(BaseTool):
    name: str = "list_documents"
    description: str = (
        "List reference documents available in the knowledge directory "
        "(overviews, data dictionaries, runbooks, methodology notes). Use this "
        "to discover what reference material you can read with read_document."
    )
    args_schema: Type[BaseModel] = ListDocumentsInput
    settings: Optional[Settings] = None

    def _run(self, subdir: Optional[str] = None) -> str:
        s = self.settings or get_settings()
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


class ReadDocumentInput(BaseModel):
    path: str = Field(
        ...,
        description=(
            "Path of the document relative to the knowledge dir, e.g. "
            "'shared/desk_overview.md' (as returned by list_documents)."
        ),
    )


class ReadDocumentTool(BaseTool):
    name: str = "read_document"
    description: str = (
        "Read a reference document from the knowledge directory verbatim. Use "
        "for exact details (definitions, steps, conventions) rather than "
        "paraphrasing. Call list_documents first if unsure of the path."
    )
    args_schema: Type[BaseModel] = ReadDocumentInput
    settings: Optional[Settings] = None

    def _run(self, path: str) -> str:
        s = self.settings or get_settings()
        base = s.knowledge_dir.resolve()
        target = (base / path).resolve()
        # Prevent path traversal outside the knowledge directory.
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
