"""CrewAI tool: read-only SQL Server (T-SQL) queries (legacy source)."""

from __future__ import annotations

import urllib.parse
from typing import Any, Dict, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config.settings import Settings, get_settings
from ..utils.logging import get_logger
from ._sql_common import assert_read_only, load_named_query, summarize_and_persist

logger = get_logger(__name__)


class SQLServerQueryInput(BaseModel):
    query_name: Optional[str] = Field(
        None,
        description=(
            "Name of a .sql file in sql/sqlserver/ (without extension)."
        ),
    )
    sql: Optional[str] = Field(
        None, description="Ad-hoc read-only T-SQL (SELECT/WITH only)."
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Named bind parameters for :name placeholders."
    )
    row_limit: int = Field(1000, description="Safety cap on returned rows.")


class SQLServerQueryTool(BaseTool):
    name: str = "sqlserver_query"
    description: str = (
        "Query the legacy Microsoft SQL Server databases for Secondary Market "
        "loan and pricing data. Use this for data still on SQL Server (not yet "
        "migrated to Snowflake); prefer snowflake_query when the data is in "
        "Snowflake. Provide a named query from sql/sqlserver/ (query_name) plus "
        "params, or ad-hoc read-only T-SQL (sql). Named binds use :name style "
        "and T-SQL uses TOP (not LIMIT). Returns a summary, preview, and CSV path."
    )
    args_schema: Type[BaseModel] = SQLServerQueryInput
    settings: Optional[Settings] = None

    def _odbc_connect_string(self, s: Settings) -> str:
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

    def _engine(self, s: Settings):
        from sqlalchemy import create_engine

        odbc = urllib.parse.quote_plus(self._odbc_connect_string(s))
        url = f"mssql+pyodbc:///?odbc_connect={odbc}"
        return create_engine(url, pool_pre_ping=True)

    def _run(
        self,
        query_name: Optional[str] = None,
        sql: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        row_limit: int = 1000,
    ) -> str:
        s = self.settings or get_settings()
        if not query_name and not sql:
            return "Error: no query provided. Pass either 'query_name' or 'sql'."

        try:
            query = sql if sql else load_named_query(s.sql_server_dir, query_name)
            assert_read_only(query, "SQL Server")
        except (FileNotFoundError, PermissionError) as exc:
            return f"Error: {exc}"

        if not s.sqlserver_configured:
            return (
                "Error: SQL Server is not configured (set SQL_SERVER_HOST, "
                "SQL_SERVER_DATABASE, and either SQL_SERVER_TRUSTED_CONNECTION "
                "or SQL_SERVER_USER/SQL_SERVER_PASSWORD in .env). Resolved query "
                "was:\n" + query.strip()
            )

        bind = dict(params or {})
        bind.setdefault("row_limit", row_limit)

        try:
            import pandas as pd
            from sqlalchemy import text

            engine = self._engine(s)
        except Exception as exc:  # pragma: no cover - depends on local drivers
            logger.exception("SQL Server engine setup failed")
            return f"Error: connection setup failed: {exc}"

        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=bind)
            if row_limit and len(df) > row_limit:
                df = df.head(row_limit)
        except Exception as exc:  # pragma: no cover - depends on live data
            logger.exception("Query execution failed")
            return f"Error: query failed: {exc}"
        finally:
            engine.dispose()

        return summarize_and_persist(
            df, s.artifacts_dir, query_name or "sqlserver_adhoc"
        )
