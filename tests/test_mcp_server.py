"""Smoke test: the MCP server imports and registers the expected tools."""

import asyncio


def test_mcp_server_registers_all_tools():
    from pennymac_agent.mcp_server import mcp

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "snowflake_query",
        "sqlserver_query",
        "list_sql_queries",
        "excel_model",
        "describe_excel_models",
        "run_vba_macro",
        "generate_vba",
        "list_documents",
        "read_document",
    }
    assert expected <= names
