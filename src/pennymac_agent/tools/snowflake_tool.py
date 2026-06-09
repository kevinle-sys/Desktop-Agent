"""Snowflake query tool (plain function for the MCP server)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..config.settings import get_settings
from ..utils.logging import get_logger
from ._sql_common import assert_read_only, load_named_query, summarize_and_persist

logger = get_logger(__name__)


def _connect(s):
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


def snowflake_query(
    query_name: Optional[str] = None,
    sql: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    row_limit: int = 1000,
) -> str:
    """Run a read-only query against the Snowflake data warehouse and return a summary.

    Provide EITHER a named query from the sql/snowflake/ library (query_name)
    plus optional params, OR an ad-hoc read-only SQL string (sql). Named bind
    parameters use %(name)s style. Mutating statements are rejected. Returns a
    row/column summary, a 10-row preview, and the path to a saved CSV of the
    full result.

    Args:
        query_name: Name of a .sql file in sql/snowflake/ (without extension).
        sql: Ad-hoc read-only SQL (SELECT/WITH only).
        params: Named bind parameters for %(name)s placeholders.
        row_limit: Safety cap on returned rows (default 1000).
    """
    s = get_settings()
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
        conn = _connect(s)
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

    return summarize_and_persist(df, s.artifacts_dir, query_name or "snowflake_adhoc")
