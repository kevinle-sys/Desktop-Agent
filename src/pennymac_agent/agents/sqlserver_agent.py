"""SQL Server Data Agent (legacy source during the Snowflake transition).

Mirrors the Snowflake agent but targets Microsoft SQL Server via SQLAlchemy +
pyodbc. Supports both SQL logins and Windows/integrated (trusted) auth, runs
parameterized T-SQL for loan/pricing data, and returns a pandas DataFrame.
Built for read-only analytics: data-mutating statements are rejected by default.

Note on parameters: SQL Server templates use named binds in ``:name`` form
(SQLAlchemy style), e.g. ``SELECT TOP (:row_limit) ... WHERE product = :product``.
This differs from the Snowflake agent, which uses ``%(name)s``.
"""

from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

from ..config.settings import Settings, get_settings
from ..utils.logging import get_logger
from .base_agent import AgentResult, BaseAgent

logger = get_logger(__name__)

# Statements that mutate data/schema; blocked unless explicitly allowed.
_FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|UPDATE|INSERT|MERGE|ALTER|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


class SQLServerAgent(BaseAgent):
    name = "sqlserver_query"
    description = (
        "Query the legacy Microsoft SQL Server databases for Secondary Market "
        "loan and pricing data. Use this when the data still lives in SQL "
        "Server (not yet migrated to Snowflake). Prefer 'snowflake_query' when "
        "the same data is available in Snowflake; use this for SQL-Server-only "
        "sources. Provide either a named query from the sql/sqlserver/ library "
        "(query_name) plus its params, or an ad-hoc read-only T-SQL string "
        "(sql). Named bind parameters use :name style. Returns a DataFrame."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query_name": {
                "type": "string",
                "description": (
                    "Name of a .sql file in the sql/sqlserver/ directory "
                    "(without extension), e.g. 'locked_loans_by_product'."
                ),
            },
            "sql": {
                "type": "string",
                "description": "Ad-hoc read-only T-SQL (SELECT/WITH only).",
            },
            "params": {
                "type": "object",
                "description": (
                    "Named bind parameters for :name placeholders, e.g. "
                    "{'product': 'FN30', 'row_limit': 50}."
                ),
            },
            "row_limit": {
                "type": "integer",
                "description": "Safety cap on returned rows (default 1000).",
                "default": 1000,
            },
        },
        "additionalProperties": False,
    }

    def __init__(self, settings: Optional[Settings] = None, allow_writes: bool = False):
        self.settings = settings or get_settings()
        self.allow_writes = allow_writes

    # --- helpers --------------------------------------------------------------
    def _assert_read_only(self, sql: str) -> None:
        if self.allow_writes:
            return
        match = _FORBIDDEN.search(sql)
        if match:
            raise PermissionError(
                f"Refusing to run '{match.group(0).upper()}' statement; the "
                "SQL Server agent is read-only by default."
            )

    def _load_named_query(self, query_name: str) -> str:
        safe = Path(query_name).name  # strip any path traversal
        path = self.settings.sql_server_dir / f"{safe}.sql"
        if not path.exists():
            raise FileNotFoundError(f"No SQL template found at {path}")
        return path.read_text(encoding="utf-8")

    def _odbc_connect_string(self) -> str:
        s = self.settings
        server = s.sqlserver_host or ""
        if s.sqlserver_port:
            server = f"{server},{s.sqlserver_port}"
        parts = [
            f"DRIVER={{{s.sqlserver_driver}}}",
            f"SERVER={server}",
            f"DATABASE={s.sqlserver_database}",
        ]
        if s.sqlserver_trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={s.sqlserver_user}")
            parts.append(f"PWD={s.sqlserver_password}")
        parts.append("Encrypt=" + ("yes" if s.sqlserver_encrypt else "no"))
        if s.sqlserver_trust_server_certificate:
            parts.append("TrustServerCertificate=yes")
        return ";".join(parts)

    def _engine(self):
        """Build a SQLAlchemy engine over pyodbc (lazy import)."""
        from sqlalchemy import create_engine

        odbc = urllib.parse.quote_plus(self._odbc_connect_string())
        url = f"mssql+pyodbc:///?odbc_connect={odbc}"
        # fast_executemany is irrelevant for reads; pool_pre_ping guards stale
        # connections on a flaky corporate network.
        return create_engine(url, pool_pre_ping=True)

    # --- main entrypoint ------------------------------------------------------
    def run(  # type: ignore[override]
        self,
        query_name: Optional[str] = None,
        sql: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        row_limit: int = 1000,
        **_: Any,
    ) -> AgentResult:
        if not query_name and not sql:
            return AgentResult.failure(
                "No query provided. Pass either 'query_name' or 'sql'."
            )

        try:
            query = sql if sql else self._load_named_query(query_name)  # type: ignore[arg-type]
            self._assert_read_only(query)
        except (FileNotFoundError, PermissionError) as exc:
            return AgentResult.failure(str(exc))

        if not self.settings.sqlserver_configured:
            return AgentResult.failure(
                "SQL Server is not configured (set SQL_SERVER_HOST, "
                "SQL_SERVER_DATABASE, and either SQL_SERVER_TRUSTED_CONNECTION "
                "or SQL_SERVER_USER/SQL_SERVER_PASSWORD in .env). Resolved "
                "query was:\n" + query.strip()
            )

        bind = dict(params or {})
        bind.setdefault("row_limit", row_limit)

        try:
            import pandas as pd
            from sqlalchemy import text

            engine = self._engine()
        except Exception as exc:  # pragma: no cover - depends on local drivers
            logger.exception("SQL Server engine setup failed")
            return AgentResult.failure(f"Connection setup failed: {exc}")

        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=bind)
            if row_limit and len(df) > row_limit:
                df = df.head(row_limit)
        except Exception as exc:  # pragma: no cover - depends on live data
            logger.exception("Query execution failed")
            return AgentResult.failure(f"Query failed: {exc}")
        finally:
            engine.dispose()

        summary = (
            f"Returned {len(df)} rows x {len(df.columns)} cols. "
            f"Columns: {list(df.columns)}. "
            f"Preview:\n{df.head(10).to_string(index=False)}"
        )
        return AgentResult.success(summary, data=df, rows=len(df))
