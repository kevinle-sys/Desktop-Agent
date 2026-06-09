"""Tool-function tests that need no live DB, Excel, or LLM.

The read-only guardrail, not-configured handling, registry resolution, and
document access all run before any driver/network call, so these execute
offline. Settings read OS env / .env; for the DB guardrail tests we just need
the validation to run before any connection.
"""

from pennymac_agent.tools import (
    describe_excel_models,
    list_documents,
    list_sql_queries,
    read_document,
    snowflake_query,
    sqlserver_query,
)


# --- SQL guardrails ----------------------------------------------------------
def test_snowflake_blocks_writes():
    out = snowflake_query(sql="DELETE FROM secondary.locks")
    assert "read-only" in out.lower()


def test_snowflake_requires_a_query():
    out = snowflake_query()
    assert "no query" in out.lower()


def test_sqlserver_blocks_writes():
    out = sqlserver_query(sql="UPDATE dbo.locks SET upb = 0")
    assert "read-only" in out.lower()


# --- Discovery ----------------------------------------------------------------
def test_list_sql_queries_finds_named_templates():
    out = list_sql_queries(engine="snowflake")
    assert "locked_loans_by_product" in out


def test_describe_excel_models_lists_registry():
    out = describe_excel_models()
    assert "fn30_pricing" in out
    assert "macros" in out.lower()


# --- Documents ----------------------------------------------------------------
def test_list_and_read_documents():
    listing = list_documents(subdir="shared")
    assert "desk_overview.md" in listing
    body = read_document(path="shared/desk_overview.md")
    assert "Secondary Market Desk" in body


def test_read_document_blocks_traversal():
    out = read_document(path="../pyproject.toml")
    assert "escapes" in out.lower() or "not found" in out.lower()
