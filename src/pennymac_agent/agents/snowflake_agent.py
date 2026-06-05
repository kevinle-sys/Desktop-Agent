"""Snowflake / SQL Data Agent.

Handles secure Snowflake connections, executes parameterized SQL for loan and
pricing data, and returns results as a pandas DataFrame. Built for read-only
analytics: data-mutating statements are rejected by default.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

from ..config.settings import Settings, get_settings
from ..utils.logging import get_logger
from .base_agent import AgentResult, BaseAgent

logger = get_logger(__name__)

# Statements that mutate data/schema; blocked unless explicitly allowed.
_FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|UPDATE|INSERT|MERGE|ALTER|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class SnowflakeAgent(BaseAgent):
    name = "snowflake_query"
    description = (
        "Query the Snowflake data warehouse for Secondary Market loan and "
        "pricing data. Use this whenever the trader needs to pull, filter, or "
        "aggregate loans, locks, pricing, or market data. Provide either a "
        "named query from the sql/ library (query_name) plus its params, or an "
        "ad-hoc read-only SQL string (sql). Returns a pandas DataFrame."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query_name": {
                "type": "string",
                "description": (
                    "Name of a .sql file in the sql/ directory (without "
                    "extension), e.g. 'locked_loans_by_product'."
                ),
            },
            "sql": {
                "type": "string",
                "description": "Ad-hoc read-only SQL (SELECT/WITH only).",
            },
            "params": {
                "type": "object",
                "description": (
                    "Named bind parameters for %(name)s placeholders, e.g. "
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
                "Snowflake agent is read-only by default."
            )

    def _load_named_query(self, query_name: str) -> str:
        safe = Path(query_name).name  # strip any path traversal
        path = self.settings.sql_dir / f"{safe}.sql"
        if not path.exists():
            raise FileNotFoundError(f"No SQL template found at {path}")
        return path.read_text(encoding="utf-8")

    def _connect(self):
        """Open a Snowflake connection from settings (lazy import)."""
        import snowflake.connector

        cfg: Dict[str, Any] = {
            "account": self.settings.snowflake_account,
            "user": self.settings.snowflake_user,
            "role": self.settings.snowflake_role,
            "warehouse": self.settings.snowflake_warehouse,
            "database": self.settings.snowflake_database,
            "schema": self.settings.snowflake_schema,
        }
        if self.settings.snowflake_authenticator:
            cfg["authenticator"] = self.settings.snowflake_authenticator
        if self.settings.snowflake_password:
            cfg["password"] = self.settings.snowflake_password
        # TODO: key-pair auth — load SNOWFLAKE_PRIVATE_KEY_PATH and pass
        # private_key=... when password auth is not used.
        cfg = {k: v for k, v in cfg.items() if v is not None}
        return snowflake.connector.connect(**cfg)

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

        if not self.settings.snowflake_configured:
            return AgentResult.failure(
                "Snowflake is not configured (set SNOWFLAKE_ACCOUNT and "
                "SNOWFLAKE_USER in .env). Resolved query was:\n" + query.strip()
            )

        bind = dict(params or {})
        bind.setdefault("row_limit", row_limit)

        try:
            conn = self._connect()
        except Exception as exc:  # pragma: no cover - depends on live network
            logger.exception("Snowflake connection failed")
            return AgentResult.failure(f"Connection failed: {exc}")

        try:
            cur = conn.cursor()
            cur.execute(query, bind)
            df = cur.fetch_pandas_all()
            if row_limit and len(df) > row_limit:
                df = df.head(row_limit)
        except Exception as exc:  # pragma: no cover - depends on live data
            logger.exception("Query execution failed")
            return AgentResult.failure(f"Query failed: {exc}")
        finally:
            conn.close()

        summary = (
            f"Returned {len(df)} rows x {len(df.columns)} cols. "
            f"Columns: {list(df.columns)}. "
            f"Preview:\n{df.head(10).to_string(index=False)}"
        )
        return AgentResult.success(summary, data=df, rows=len(df))
