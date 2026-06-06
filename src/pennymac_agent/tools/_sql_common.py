"""Shared helpers for the SQL data tools (guardrail + named-query loading)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Statements that mutate data/schema; blocked unless explicitly allowed.
FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|UPDATE|INSERT|MERGE|ALTER|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


def assert_read_only(sql: str, engine: str) -> None:
    """Raise PermissionError if ``sql`` contains a mutating statement."""
    match = FORBIDDEN.search(sql)
    if match:
        raise PermissionError(
            f"Refusing to run '{match.group(0).upper()}' statement; the "
            f"{engine} tool is read-only."
        )


def load_named_query(sql_dir: Path, query_name: str) -> str:
    """Load a named .sql template from ``sql_dir`` (path-traversal safe)."""
    safe = Path(query_name).name
    path = sql_dir / f"{safe}.sql"
    if not path.exists():
        raise FileNotFoundError(f"No SQL template found at {path}")
    return path.read_text(encoding="utf-8")


def summarize_and_persist(
    df: pd.DataFrame, artifacts_dir: Path, name: str
) -> str:
    """Persist a result DataFrame for agent handoff and return a text summary.

    The summary is what the agent sees; large data stays out of the LLM context.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name) or "result"
    out_path = artifacts_dir / f"{safe}.csv"
    try:
        df.to_csv(out_path, index=False)
        saved = f" Saved to: {out_path}"
    except Exception:  # pragma: no cover - disk issues shouldn't fail the query
        saved = " (could not persist result to disk)"
    preview = df.head(10).to_string(index=False) if len(df) else "(no rows)"
    return (
        f"Returned {len(df)} rows x {len(df.columns)} cols. "
        f"Columns: {list(df.columns)}.{saved}\nPreview:\n{preview}"
    )
