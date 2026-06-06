"""Knowledge (RAG) wiring for CrewAI agents.

Reference documents live under the knowledge directory in two tiers:
- ``knowledge/shared/``        -> baseline context attached to the whole crew
- ``knowledge/<specialist>/``  -> per-agent context (e.g. knowledge/data_analyst/)

Files are turned into CrewAI knowledge sources and embedded at run time. Because
CrewAI resolves string file paths relative to a top-level ``knowledge/`` folder,
we pass paths relative to ``settings.knowledge_dir``.

All of this is optional: if knowledge is disabled, the directory is missing, or
no embedding API key is configured, the helpers return empty/None so the crew
still runs without RAG.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .config.settings import Settings, get_settings
from .utils.logging import get_logger

logger = get_logger(__name__)

# Map a file suffix to the CrewAI knowledge source class that handles it.
_TEXT_SUFFIXES = {".md", ".txt"}
_PDF_SUFFIXES = {".pdf"}
_CSV_SUFFIXES = {".csv"}

SHARED_SUBDIR = "shared"


def build_embedder(settings: Optional[Settings] = None) -> Optional[Dict[str, Any]]:
    """Return a CrewAI embedder config dict, or None when not available."""
    settings = settings or get_settings()
    if not settings.knowledge_available:
        return None
    return {
        "provider": settings.embedding_provider,
        "config": {
            "api_key": settings.embedding_key,
            "model_name": settings.embedding_model,
        },
    }


def _sources_from_dir(settings: Settings, subdir: str) -> List[Any]:
    """Build knowledge sources for every supported file in knowledge/<subdir>."""
    folder = settings.knowledge_dir / subdir
    if not folder.exists():
        return []

    text_paths: List[str] = []
    pdf_paths: List[str] = []
    csv_paths: List[str] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        # CrewAI resolves string paths relative to the knowledge dir.
        rel = str(path.relative_to(settings.knowledge_dir)).replace("\\", "/")
        suffix = path.suffix.lower()
        if suffix in _TEXT_SUFFIXES:
            text_paths.append(rel)
        elif suffix in _PDF_SUFFIXES:
            pdf_paths.append(rel)
        elif suffix in _CSV_SUFFIXES:
            csv_paths.append(rel)

    sources: List[Any] = []
    try:
        if text_paths:
            from crewai.knowledge.source.text_file_knowledge_source import (
                TextFileKnowledgeSource,
            )

            sources.append(TextFileKnowledgeSource(file_paths=text_paths))
        if pdf_paths:
            from crewai.knowledge.source.pdf_knowledge_source import (
                PDFKnowledgeSource,
            )

            sources.append(PDFKnowledgeSource(file_paths=pdf_paths))
        if csv_paths:
            from crewai.knowledge.source.csv_knowledge_source import (
                CSVKnowledgeSource,
            )

            sources.append(CSVKnowledgeSource(file_paths=csv_paths))
    except Exception as exc:  # pragma: no cover - defensive against load errors
        logger.warning("Could not build knowledge sources for '%s': %s", subdir, exc)
        return []
    return sources


def shared_sources(settings: Optional[Settings] = None) -> List[Any]:
    """Knowledge sources shared across the whole crew (baseline context)."""
    settings = settings or get_settings()
    if not settings.knowledge_available:
        return []
    return _sources_from_dir(settings, SHARED_SUBDIR)


def agent_sources(
    specialist_key: str, settings: Optional[Settings] = None
) -> List[Any]:
    """Knowledge sources specific to one specialist (knowledge/<key>/)."""
    settings = settings or get_settings()
    if not settings.knowledge_available:
        return []
    return _sources_from_dir(settings, specialist_key)
