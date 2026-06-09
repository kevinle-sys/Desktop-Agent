"""MCP server exposing the PennyMac trading tools to Cursor subagents.

Run over stdio; Cursor connects via .cursor/mcp.json. Each tool is a plain
function from ``pennymac_agent.tools`` registered with FastMCP, which builds the
JSON schema from the function signature and docstring.

Tools exposed:
  - snowflake_query / sqlserver_query   (read-only data)
  - list_sql_queries                    (discover the query library)
  - excel_model / describe_excel_models (pricing models)
  - run_vba_macro / generate_vba        (automation)
  - list_documents / read_document      (reference docs incl. legacy queries)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .tools import (
    describe_excel_models,
    excel_model,
    generate_vba,
    list_documents,
    list_sql_queries,
    read_document,
    run_vba_macro,
    snowflake_query,
    sqlserver_query,
)

mcp = FastMCP("pennymac-trading")

# Register each tool function (schema is introspected from the signature).
for _fn in (
    snowflake_query,
    sqlserver_query,
    list_sql_queries,
    excel_model,
    describe_excel_models,
    run_vba_macro,
    generate_vba,
    list_documents,
    read_document,
):
    mcp.tool()(_fn)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
