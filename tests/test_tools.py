"""Tool-level tests that need no live DB, Excel, or LLM API key.

The read-only guardrail, not-configured handling, and registry resolution all
run before any driver/network call, so these execute offline.
"""

from pennymac_agent.config.settings import Settings
from pennymac_agent.tools import (
    DescribeExcelModelsTool,
    ExcelModelTool,
    ListDocumentsTool,
    ListSQLQueriesTool,
    ReadDocumentTool,
    SnowflakeQueryTool,
    SQLServerQueryTool,
)


def _no_db_settings() -> Settings:
    return Settings(
        SNOWFLAKE_ACCOUNT=None,
        SNOWFLAKE_USER=None,
        SQL_SERVER_HOST=None,
        SQL_SERVER_DATABASE=None,
        SQL_SERVER_USER=None,
        SQL_SERVER_PASSWORD=None,
        SQL_SERVER_TRUSTED_CONNECTION=False,
    )


# --- Snowflake tool -----------------------------------------------------------
def test_snowflake_blocks_writes():
    tool = SnowflakeQueryTool(settings=_no_db_settings())
    out = tool._run(sql="DELETE FROM secondary.locks")
    assert "read-only" in out.lower()


def test_snowflake_requires_a_query():
    tool = SnowflakeQueryTool(settings=_no_db_settings())
    out = tool._run()
    assert "no query" in out.lower()


def test_snowflake_reports_not_configured():
    tool = SnowflakeQueryTool(settings=_no_db_settings())
    out = tool._run(sql="SELECT 1 AS one")
    assert "not configured" in out.lower()


# --- SQL Server tool ----------------------------------------------------------
def test_sqlserver_blocks_writes():
    tool = SQLServerQueryTool(settings=_no_db_settings())
    out = tool._run(sql="UPDATE dbo.locks SET upb = 0")
    assert "read-only" in out.lower()


def test_sqlserver_reports_not_configured():
    tool = SQLServerQueryTool(settings=_no_db_settings())
    out = tool._run(sql="SELECT 1 AS one")
    assert "not configured" in out.lower()


# --- Excel tool ---------------------------------------------------------------
def test_excel_unknown_model():
    # Uses the real models/registry.yaml; an unknown key should be rejected
    # before any Excel interaction.
    tool = ExcelModelTool(settings=Settings())
    out = tool._run(model_name="definitely_not_a_model")
    assert "not registered" in out.lower()


# --- Discovery tools ----------------------------------------------------------
def test_list_sql_queries_finds_named_templates():
    out = ListSQLQueriesTool(settings=Settings())._run(engine="snowflake")
    assert "locked_loans_by_product" in out


def test_describe_excel_models_lists_registry():
    out = DescribeExcelModelsTool(settings=Settings())._run()
    assert "fn30_pricing" in out
    assert "macros" in out.lower()


# --- Document tools -----------------------------------------------------------
def test_list_and_read_documents():
    s = Settings()
    listing = ListDocumentsTool(settings=s)._run(subdir="shared")
    assert "desk_overview.md" in listing
    body = ReadDocumentTool(settings=s)._run(path="shared/desk_overview.md")
    assert "Secondary Market Desk" in body


def test_read_document_blocks_traversal():
    out = ReadDocumentTool(settings=Settings())._run(path="../pyproject.toml")
    assert "escapes" in out.lower() or "not found" in out.lower()
