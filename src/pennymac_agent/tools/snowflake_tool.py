"""CrewAI tool: read-only Snowflake queries returning a preview + saved file."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config.settings import Settings, get_settings
from ..utils.logging import get_logger
from ._sql_common import assert_read_only, load_named_query, summarize_and_persist

logger = get_logger(__name__)


class SnowflakeQueryInput(BaseModel):
    query_name: Optional[str] = Field(
        None,
        description=(
            "Name of a .sql file in sql/snowflake/ (without extension), e.g. "
            "'locked_loans_by_product'."
        ),
    )
    sql: Optional[str] = Field(
        None, description="Ad-hoc read-only SQL (SELECT/WITH only)."
    )
    params: Optional[Dict[str, Any]] = Field(
        None,
        description="Named bind parameters for %(name)s placeholders.",
    )
    row_limit: int = Field(1000, description="Safety cap on returned rows.")


class SnowflakeQueryTool(BaseTool):
    name: str = "snowflake_query"
    description: str = (
        "Query the Snowflake data warehouse for Secondary Market loan and "
        "pricing data. Provide either a named query from the sql/snowflake/ "
        "library (query_name) plus params, or an ad-hoc read-only SQL string "
        "(sql). Named binds use %(name)s style. Returns a row/column summary, a "
        "10-row preview, and the path to a saved CSV of the full result."
    )
    args_schema: Type[BaseModel] = SnowflakeQueryInput
    settings: Optional[Settings] = None

    def _connect(self, s: Settings):
        import snowflake.connector

        cfg: Dict[str, Any] = {
            "account": s.snowflake_account,
            "user": s.snowflake_user,
            "role": s.snowflake_role,
            "warehouse": s.snowflake_warehouse,
            "database": s.snowflake_database,
            "schema": s.snowflake_schema,
        }
        if s.snowflake_authenticator:
            cfg["authenticator"] = s.snowflake_authenticator
        if s.snowflake_password:
            cfg["password"] = s.snowflake_password
        cfg = {k: v for k, v in cfg.items() if v is not None}
        return snowflake.connector.connect(**cfg)

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
            query = sql if sql else load_named_query(s.sql_dir, query_name)
            assert_read_only(query, "Snowflake")
        except (FileNotFoundError, PermissionError) as exc:
            return f"Error: {exc}"

        if not s.snowflake_configured:
            return (
                "Error: Snowflake is not configured (set SNOWFLAKE_ACCOUNT and "
                "SNOWFLAKE_USER in .env). Resolved query was:\n" + query.strip()
            )

        bind = dict(params or {})
        bind.setdefault("row_limit", row_limit)

        try:
            conn = self._connect(s)
        except Exception as exc:  # pragma: no cover - depends on live network
            logger.exception("Snowflake connection failed")
            return f"Error: connection failed: {exc}"

        try:
            cur = conn.cursor()
            cur.execute(query, bind)
            df = cur.fetch_pandas_all()
            if row_limit and len(df) > row_limit:
                df = df.head(row_limit)
        except Exception as exc:  # pragma: no cover - depends on live data
            logger.exception("Query execution failed")
            return f"Error: query failed: {exc}"
        finally:
            conn.close()

        return summarize_and_persist(
            df, s.artifacts_dir, query_name or "snowflake_adhoc"
        )
