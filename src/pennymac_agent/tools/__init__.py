"""Tool functions exposing the desk's data, modeling, and automation capabilities.

These are plain Python functions (no agent framework). The MCP server in
``pennymac_agent.mcp_server`` registers them so Cursor subagents can call them.
"""

from .discovery_tool import describe_excel_models, list_sql_queries
from .docs_tool import list_documents, read_document
from .excel_tool import excel_model
from .snowflake_tool import snowflake_query
from .sqlserver_tool import sqlserver_query
from .vba_tool import generate_vba, run_vba_macro

__all__ = [
    "snowflake_query",
    "sqlserver_query",
    "excel_model",
    "run_vba_macro",
    "generate_vba",
    "list_sql_queries",
    "describe_excel_models",
    "list_documents",
    "read_document",
]
